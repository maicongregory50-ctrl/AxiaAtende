-- #1722 -- a VOLTA da 075: a logo da ficha de 24/11 volta a esperar o cliente. Sem BEGIN nem COMMIT.
UPDATE atendimento.logos_de_cliente
   SET pergunta_pendente = 'erp_codigo', puxada_em = NULL, erro = ''
 WHERE wamid = 'wamid.HBgMNTU0OTkxNTA1NTY1FQIAEhgWM0VCMDUzRERFRDNEQzBDMjQyNTk3MQA='
   AND erro = 'nao era logo: PDF deslizando o aviso da integracao (#1722)';
DELETE FROM casa.mudancas WHERE nome = '075_logo_ficha_1722.sql';
