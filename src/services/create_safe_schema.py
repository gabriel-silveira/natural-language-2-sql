from src.config import SCHEMA_SAFE_PASSWORD

original_schema = "verx_rh"
safe_schema = "verx_rh_safe"
safe_user = "gabriel_safe"

# supondo que as tabelas originais estejam no schema original
create_safe_schema = f"CREATE SCHEMA IF NOT EXISTS {safe_schema};"

# CAMPOS REMOVIDOS NO SCHEMA SAFE
# valor_atual,
# pretensao_hora,
# pretensao_mensal,
# senha,

# VIEW sem campos de compensação
create_view_candidates = f"""
CREATE OR REPLACE VIEW {safe_schema}.candidatos AS
SELECT
  id_candidato,
  nome,
  rg,
  rg_orgao_emissor,
  rg_uf,
  numero_passaporte,
  filiacao1,
  filiacao2,
  data_nascimento,
  nacionalidade,
  genero,
  estado_civil,
  endereco,
  email,
  telefone_residencial,
  telefone_recados,
  celular,
  como_conheceu,
  como_conheceu_outro,
  receber_informativos,
  mini_curriculo,
  nivel_consultor,
  disponibilidade_viagens,
  vinculo_atual,
  vinculo_pretendido,
  possui_empresa,
  cnpj_empresa,
  cpf_restricao,
  lista_restricao,
  tipo_empresa,
  cpf,
  cadastro_realizado_em,
  ultima_alteracao_em,
  classificacao,
  objetivo,
  meio_conhecimento,
  linkedin,
  skype,
  email_secundario,
  raca,
  necessidade,
  data_indicacao,
  consultor_indicacao,
  receber_whats,
  contato_emergencia
FROM {original_schema}.candidatos;
"""

# usuário do app (ajuste host conforme seu deploy)
create_user = f"CREATE USER IF NOT EXISTS '{safe_user}'@'localhost' IDENTIFIED BY '{SCHEMA_SAFE_PASSWORD}';"

# Remova privilégios herdados
revoke_privileges = f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{safe_user}'@'localhost';"

# Conceda apenas SELECT no schema seguro (e nada no schema original)
grant_select = f"GRANT SELECT ON {safe_schema}.* TO '{safe_user}'@'localhost';"

grant_show_view = f"GRANT SHOW VIEW ON {safe_schema}.* TO '{safe_user}'@'localhost';"

flush = "FLUSH PRIVILEGES;"
