ALTER TABLE posts ADD COLUMN best_id varchar(32);
INSERT INTO migrations (version) VALUES (6);
