# gitlab-reports
Creates reports on spent time for Gitlab issues by author.

This work began from the great job of https://gitlab.com/incomprehensibleaesthetics/gitlab-cli-reports, but then we went to a Jupyter version.

## Example report

<img src="sample1.png" width=600 />

## Usage

* Create a docker-compose.yml file

```
version: '3.6'
services:
  gitlab-reports:
    image: flaviostutz/gitlab-reports
```

* Run ```docker-compose up```

* See report on console output

## ENVs

* JUPYTER_TOKEN - Jupyter password. required
