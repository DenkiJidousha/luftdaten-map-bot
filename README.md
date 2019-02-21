# luftdaten-map-bot

## Background

[Luftdaten Airrohr](https://luftdaten.info/en/home-en/) is a citizen science
open data project started in Germany by [Code for Germany - Open Data
Stuttgart](https://codefor.de/en/stuttgart/).

Using parts you can order over the internet for around £30 / €30, volunteers
build and host simple DIY particle pollution sensors which record PM2.5 and PM10
fine particle levels. There are often local groups running workshops, but you can
follow the [DIY sensor build instructions](https://luftdaten.info/en/construction-manual/).

This international network of sensors submits their measurements via their host
wifi to the project's central server. If you have registered your sensor on the
network with location information (slightly obscured for privacy), it will appear
on the [Luftdaten public map](https://maps.luftdaten.info) showing hourly mean
PM2.5 values. For computer programs, there is also a [Luftdaten.info
API](https://github.com/opendata-stuttgart/meta/wiki/APIs), which we use here.

This repository is a project to render Luftdaten Airrohr PM pollution data maps
(duplicating the look and feel of https://maps.luftdaten.info with its hexagons)
for specific preconfigured regions as images which can then be used in automated
reports or Tweets.

## Code

This is a simple Python project, using [black](https://github.com/ambv/black) for
the code formatting.
