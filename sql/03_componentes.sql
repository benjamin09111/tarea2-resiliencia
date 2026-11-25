-- Componente conexa de cada vertice por escenario. RF = fibra + acometidas a fibra; RE = todas las capas.
ALTER TABLE red_noded_vertices_pgr DROP COLUMN IF EXISTS comp_rf, DROP COLUMN IF EXISTS comp_re;
ALTER TABLE red_noded_vertices_pgr ADD COLUMN comp_rf integer, ADD COLUMN comp_re integer;
UPDATE red_noded_vertices_pgr v SET comp_rf = c.component FROM pgr_connectedComponents(
  'SELECT id, source, target, 1 AS cost, 1 AS reverse_cost FROM red_noded WHERE capa IN (''fibra'',''acometida'')') c WHERE c.node = v.id;
UPDATE red_noded_vertices_pgr v SET comp_re = c.component FROM pgr_connectedComponents(
  'SELECT id, source, target, 1 AS cost, 1 AS reverse_cost FROM red_noded') c WHERE c.node = v.id;
