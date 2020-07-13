import argparse
import gitlab
import re

def fetch_time_entries(gl, filter_by_author=None, filter_by_date_begin=None, filter_by_date_end=None, filter_by_project_membership=False, filter_by_search=None, filter_by_milestone=None, debug=False):
  time_entries = []

  # Iterate through projects and fetch their issues because directly fetching
  # issues only returns issues created by the token owner.
  if debug:
    print('Getting projects. search=%s only_member=%s' %(filter_by_search, filter_by_project_membership))
  projects = gl.projects.list(search=filter_by_search, membership=filter_by_project_membership, search_namespaces=True, lazy=False, as_list=False)
  for project in projects:
    if debug:
      print('')
      print('Getting issues for project=%s' %(project.name), end =" ")
    issues = project.issues.list(all=True, lazy=False, as_list=False)
    if debug:
      print('(%d)'%len(issues), end = " ")

    for issue in issues:
      if debug:
        print('.', end =" ")
#       p_issue = gl.projects.get(issue.project_id, lazy=True).issues.get(issue.iid, lazy=True)
#       p_issue = issue

      # Fetch notes from oldest to newest. The order is important in case we
      # encounter a `/remove_time_spent` command.
      notes = issue.notes.list(all=True, order_by='created_at', sort='asc', as_list=False)

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
            
            milestone_title = ''
            if issue.milestone!=None:
              milestone_title = issue.milestone['title']
            
            if filter_by_milestone!=None:
              if milestone_title=='' or milestone_title!=filter_by_milestone:
                continue

            # Add a time_entry object to the result.
            time_entries.append({ 'date': date_str, 'issue_iid': issue.iid, 'duration': duration, 'issue_title': issue.title, 'note_author': note.author['username'], 'milestone_title': milestone_title })

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

