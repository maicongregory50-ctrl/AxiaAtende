-- Desfaz a 027 (#1098): sem a linha, o caminho "Mandar curriculo" volta ao "Otimo!" do pedido de sempre.
BEGIN;
DELETE FROM atendimento.respostas_da_vaga WHERE chave = 'pedir_pdf_assim';
DELETE FROM casa.mudancas WHERE nome = '027_grato_a_quem_manda_assim_mesmo.sql';
COMMIT;
