-- Modelo de falla: funciones que leen sus parametros de `parametros_modelo` (llenada desde config.json).
--   r   = sqrt(d^2 + h^2)                          distancia hipocentral (km)
--   PGA = A * exp(C * Ms) / (r + D)^B   [cm/s2]   Saragoni, Astroza y Ruiz (2004), Tabla 1, ec. (2)
--   R   = Cp*Cd*Cg * c * (PGA - a0)^b   [cortes/km] Isoyama et al. (2000), ec. (5) y Tabla 3
CREATE OR REPLACE FUNCTION par(k text) RETURNS double precision LANGUAGE sql STABLE AS
  $$ SELECT valor FROM parametros_modelo WHERE clave = k $$;

CREATE OR REPLACE FUNCTION pga_cms2(r_km double precision, ms double precision)
  RETURNS double precision LANGUAGE sql STABLE AS
  $$ SELECT par('A') * exp(par('C') * ms) / power(r_km + par('D_km'), par('B')) $$;

CREATE OR REPLACE FUNCTION tasa_cortes_km(alfa double precision)
  RETURNS double precision LANGUAGE sql STABLE AS
  $$ SELECT CASE WHEN alfa <= par('alfa0_cms2') THEN 0
            ELSE par('Cp') * par('Cd') * par('Cg') * par('c') * power(alfa - par('alfa0_cms2'), par('b')) END $$;
