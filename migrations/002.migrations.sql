CREATE TABLE migrations (
    version integer NOT NULL ,
    date timestamp DEFAULT now()
);
INSERT INTO migrations (version) VALUES (3);
