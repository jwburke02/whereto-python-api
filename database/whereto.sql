create table coordinate (
    cid int primary key,
    lat float not null,
    lng float not null
);
create table detection (
    did int primary key,
    cid int not null,
    lat float not null,
    lng float not null,
    class_name text not null,
    conf float not null,
    text_read text,
    image_url text not null
);