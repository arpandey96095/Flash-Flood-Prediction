CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS schema_version(version text primary key);
INSERT INTO schema_version(version) VALUES ('v2-flash-flood') ON CONFLICT DO NOTHING;
