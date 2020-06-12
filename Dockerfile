FROM python:3.5.9-alpine3.12
RUN apk add git

ENV GITLAB_URL 'https://gitlab.com'
ENV GITLAB_ACCESS_TOKEN ''
ENV FILTER_DATE_BEGIN ''
ENV FILTER_DATE_END ''
ENV FILTER_AUTHOR ''
ENV FILTER_ONLY_MEMBER 'true'

RUN git clone https://gitlab.com/incomprehensibleaesthetics/gitlab-cli-reports.git

WORKDIR /gitlab-cli-reports
RUN pip install gitpython python-gitlab
# RUN ./build.sh && mv dist/gitlab-cli-reports /bin/

ADD /startup.sh /

CMD [ "/startup.sh" ]
