-- Esquema base. Una tabla con las 4 capas del archivo SAIP (fibra real; el resto sintetico).
DROP TABLE IF EXISTS red CASCADE;
CREATE TABLE red (
  id        serial PRIMARY KEY,
  capa      text NOT NULL CHECK (capa IN ('fibra','postacion','camino','ferry','acometida')),
  id_origen text,                                   -- campo id del shapefile (hay repetidos en fibra)
  sintetico boolean NOT NULL,
  geom      geometry(LineString, 4326) NOT NULL
);
CREATE INDEX red_geom_gix ON red USING gist (geom);
