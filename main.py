# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Joshua Trees <joshua.trees@posteo.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import gitlab
import re
import sqlite3
import pandas as pd
# from _version import __version__


#############################################################################
## FUNCTIONS ################################################################
#############################################################################

def fetch_time_entries(gl, filter_by_author=None, filter_by_date_begin=None, filter_by_date_end=None, filter_by_project_membership=False, filter_by_search=None, debug=False):
  time_entries = []

  # Iterate through projects and fetch their issues because directly fetching
  # issues only returns issues created by the token owner.
  if debug:
    print('Getting projects. search=%s only_member=%s' %(filter_by_search, filter_by_project_membership))
  projects = gl.projects.list(search=filter_by_search, membership=filter_by_project_membership)
  for project in projects:
    if debug:
      print('')
      print('Getting issues for project=%s' %(project.name), end =" ")
    issues = project.issues.list(all=True)

    for issue in issues:
      if debug:
        print('.', end =" ")
      p_issue = gl.projects.get(issue.project_id, lazy=True).issues.get(issue.iid, lazy=True)

      # Fetch notes from oldest to newest. The order is important in case we
      # encounter a `/remove_time_spent` command.
      notes = p_issue.notes.list(all=True, order_by='created_at', sort='asc')

      for note in notes:
        if note.system:
          if note.body == 'removed time spent':
            # Remove all existing time entries for this issue. This operation
            # relies on the notes being in the correct order.
            time_entries = [e for e in time_entries if e['issue_iid'] != issue.iid]
          elif 'time spent' in note.body:
            # Skip if specified filters result in a mismatch.
            if filter_by_author and note.author['username'] != filter_by_author:
              continue

            duration = parse_duration(note.body)
            date_str = parse_date(note.body)

            if date_str:
              if filter_by_date_begin and date_str < filter_by_date_begin:
                continue
              if filter_by_date_end and date_str > filter_by_date_end:
                continue
            else:
              date_str = '<N/A>     '

            # Add a time_entry object to the result.
            time_entries.append({ 'date': date_str, 'issue_iid': issue.iid, 'duration': duration, 'issue_title': issue.title, 'note_author': note.author['username'] })

  return time_entries, projects

def format_duration(duration_in_s, tabular=False):
  hours, remainder = divmod(duration_in_s, 3600)
  minutes, seconds = divmod(remainder, 60)

  if tabular:
    return '%sh %2dm' %(hours, minutes)
  else:
    return '%sh %sm' %(hours, minutes)

def format_issue_numbers(numbers):
  return ', '.join(["#%s" %(str(n)) for n in sorted([*numbers])])

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--access-token',
                      default='token',
                      help='personal access token',
                      metavar='TOKEN',
                      required=True)
  parser.add_argument('--filter-by-author',
                      default=None,
                      help='only consider time spent by this user',
                      metavar='USERNAME')
  parser.add_argument('--filter-by-date-begin',
                      default=None,
                      help='only consider time spent on or after this date (format: YYYY-MM-DD)',
                      metavar='DATE')
  parser.add_argument('--filter-by-date-end',
                      default=None,
                      help='only consider time spent on or before this date (format: YYYY-MM-DD)',
                      metavar='DATE')
  parser.add_argument('--filter-by-search',
                      default=None,
                      help='project search keywords',
                      metavar='TEXT')
  parser.add_argument('--filter-by-project-membership',
                      action='store_const',
                      const='True',
                      help='only consider projects the member is currently a member of')
  parser.add_argument('--host-url',
                      default='https://gitlab.com',
                      help='url of the GitLab instance (default: https://gitlab.com)',
                      metavar='URL')
  parser.add_argument('--report-type',
                      default='day',
                      help='Report type. One of "issue", "day" or "user". defaults to "day"',
                      metavar='TYPE')
  parser.add_argument('--debug',
                      action='store_const',
                      const='True',
                      help='print out processing steps')
#   parser.add_argument('--version',
#                       action='version',
#                       version='%(prog)s {version}'.format(version=__version__))
  return parser.parse_args()

def parse_date(str):
  matches = re.search(r'(?<=at )\d{4}-\d{2}-\d{2}$', str)
  if matches:
    return matches.group()
  else:
    return None

def parse_duration(str):
  duration_str = re.search(r'^(?:added|subtracted) (.*) of time spent', str).group(1)
  # Map units of time to seconds.
  #
  # A time entry can have the following format:
  #   1mo 2w 3d 4h 5m 6s
  time_translations = {
    'mo': 576000,
    'w': 144000,
    'd': 28800,
    'h': 3600,
    'm': 60,
    's': 1
  }
  duration = 0
  duration_array = duration_str.split(' ')
  for duration_part in duration_array:
    # 'mo' is the only two-character unit and requires different handling.
    if duration_part[-2:] == 'mo':
      duration += int(duration_part[:-2]) * time_translations['mo']
    else:
      duration += int(duration_part[:-1]) * time_translations[duration_part[-1:]]

  if re.match(r'^subtracted', str):
    duration = -duration

  return duration

def report(entries, projects, args):

  if args.debug:
    print('Preparing SQLite database with spent time entries for doing aggregations')
  conn = sqlite3.connect(':memory:')
  c = conn.cursor()
  c.execute('''DROP TABLE IF EXISTS issue_spent''')
  c.execute('''CREATE TABLE time_entries
            (date text, issue_iid text, issue_title text, note_author text, duration integer)''')
  for entry in entries:
    c.execute("INSERT INTO time_entries VALUES ('%s','%s','%s','%s',%s)" %(entry['date'],entry['issue_iid'],entry['issue_title'],entry['note_author'],entry['duration']))
  conn.commit()
  if args.debug:
    print('DB prepared')

  pstr = ''
  first = True
  for p in projects:
    if first:
        pstr += p.name
        first = False
    else:
        pstr += ', ' + p.name

  print('')
  print('-----------------------------------------------------')
  print('  Filter:')
  print('   - Author: %s' %(args.filter_by_author))
  print('   - Period: %s to %s' %(args.filter_by_date_begin,args.filter_by_date_end))
  print('   - Search terms: %s' %(args.filter_by_search))
  print('   - Projects: %s' %(pstr))
  print('-----------------------------------------------------')
  print('')

  if args.report_type=='day':
    df = pd.read_sql_query("select * from time_entries", conn)
    df.append(df.sum(numeric_only=True), ignore_index=True)
    df['time_spent'] = df['duration'].map(format_duration)
    df.drop(['duration'], axis=0)
    print(df)
  elif args.report_type=='issue':
      print('NOT IMPLEMENTED YET')
  elif args.report_type=='user':
      print('NOT IMPLEMENTED YET')
      
  conn.close()

  print('PRINT OLD TABLE')
  if args.report_type == 'day':
    for entry in entries:
      print('%s | %s | %s' %(entry['date'],
                             entry['issue_iid'],
                             format_duration(entry['duration'])))
  elif args.report_type == 'date':
    time_spent_per_day = {}

    # Group entries by date.
    total = 0
    for entry in entries:
      date      = entry['date']
      duration  = entry['duration']
      issue_iid = entry['issue_iid']

      # Might as well do this here.
      total += duration

      if date in time_spent_per_day:
        time_spent_per_day[date]['duration'] += duration
        time_spent_per_day[date]['issues'].add(issue_iid)
      else:
        time_spent_per_day[date] = { 'duration': duration, 'issues': { issue_iid } }

    sorted_dates = sorted([*time_spent_per_day])

    # Prepare the rows and calculate how wide the issues column will have to
    # be for everything to fit in a fancy table.
    issue_column_width = 6
    for date in sorted_dates:
      issues = time_spent_per_day[date]['issues']
      issue_numbers = format_issue_numbers(issues)

      if len(issue_numbers) > issue_column_width:
        issue_column_width = len(issue_numbers)

    print('|------------|------------|-%s-|' %('-' * issue_column_width))
    print('| Date       | Time Spent | %s |' %('Issues'.ljust(issue_column_width)))
    print('|------------|------------|-%s-|' %('-' * issue_column_width))

    for date in sorted_dates:
      entry = time_spent_per_day[date]
      duration = entry['duration']
      issues = time_spent_per_day[date]['issues']

      f_duration = format_duration(duration, tabular=True).rjust(10)
      f_issue_numbers = format_issue_numbers(issues).ljust(issue_column_width)

      print('| %s | %s | %s |' %(date, f_duration, f_issue_numbers))

    print('|------------|------------|-%s-|' %('-' * issue_column_width))
    print('| Total      | %s | %s |' %(format_duration(total, tabular=True).rjust(10), ' ' * issue_column_width))
    print('|------------|------------|-%s-|' %('-' * issue_column_width))
  else:
    raise ArgumentError('Unspported value of `by`: %s' %(args.report_type))


#############################################################################
## ENTRY POINT ##############################################################
#############################################################################

args = parse_args()

if args.debug:
    print('Initializing Gitlab client...')
gl = gitlab.Gitlab(args.host_url, private_token=args.access_token)

if args.debug:
    print('Getting time entries...')
time_entries, projects = fetch_time_entries(gl,
                                  filter_by_author=args.filter_by_author,
                                  filter_by_date_begin=args.filter_by_date_begin,
                                  filter_by_date_end=args.filter_by_date_end,
                                  filter_by_project_membership=args.filter_by_project_membership,
                                  filter_by_search=args.filter_by_search,
                                  debug=args.debug)
if args.debug:
    print('')
    print('Generating report...')
report(time_entries, projects, args)
