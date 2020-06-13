FROM python:3.8.3-buster

RUN apt-get update && apt-get install -y git
RUN pip install gitpython python-gitlab pandas

# Jupyter
RUN python3 -m pip --no-cache-dir install requests notebook ipywidgets && \
    jupyter nbextension enable --py widgetsnbextension

ENV JUPYTER_TOKEN ''

ADD /startup.sh /

EXPOSE 8888

CMD [ "/startup.sh" ]
