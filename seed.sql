CREATE TABLE `hunt`
(
    `key`           TEXT PRIMARY KEY,
    `huntid`        integer,
    `worldid`       integer,
    `zoneid`        integer,
    `instanceid`    integer,
    `players`       integer,
    `currenthp`     integer,
    `maxhp`         integer,
    `lastseen`      timestamp,
    `lastfound`     timestamp,
    `lastkilled`    timestamp,
    `lastupdated`   timestamp,
    `lastuntouched` timestamp,
    `actorid`       integer,
    `status`        integer,
    `x`             float,
    `y`             float
);

CREATE TABLE `hunts`
(
    `id`        integer PRIMARY KEY,
    `name`      text,
    `rank`      integer,
    `expansion` integer,
    `spawn_min` integer,
    `spawn_max` integer
);

CREATE TABLE `zones`
(
    `id`        integer PRIMARY KEY,
    `name`      text,
    `expansion` integer,
    `mapid`     integer,
    `scale`     float,
    `offset_x`  float,
    `offset_y`  float,
    `offset_z`  float
);

CREATE TABLE `worlds`
(
    `id`           integer PRIMARY KEY,
    `name`         text,
    `datacenterid` integer,
    `regionid`     integer
);

CREATE TABLE `dcs`
(
    `id`       integer PRIMARY KEY,
    `name`     text,
    `regionid` integer
);

CREATE TABLE `regions`
(
    `id`   integer PRIMARY KEY,
    `name` text
);

CREATE TABLE 'status'
(
    'id'            integer PRIMARY KEY,
    'worldid'       integer,
    'expansion'     integer,
    'time'          timestamp,
    'status'        text
);

CREATE INDEX 'hunt_index_0' on 'hunt' ('key', 'huntid', 'worldid');
