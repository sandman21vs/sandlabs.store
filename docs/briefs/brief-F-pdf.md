# Brief — Fase F-pdf: Geração do PDF do pedido (Sonnet, worktree)

## Contexto
Repo: sandlabs.store (Flask 3 + SQLite). Leia `AGENTS.md` e `CLAUDE.md` antes.
O agente primário (Opus) fará a parte F-core (checkout como convidado,
`orders.access_token`, sessão/auth, migração). ESTE brief é SÓ a geração do PDF
— renderização pura, sem segredos, sem migração, sem lógica de pagamento.

## Objetivo
Gerar um PDF com os dados de um pedido, para o cliente que opta por NÃO criar
conta baixar como comprovante/consulta.

## Escopo / arquivos
- Adicionar `fpdf2` ao `requirements.txt`.
- NOVO `services/service_pdf.py` — função `build_order_pdf(order: dict) -> bytes`
  recebendo um dict de pedido já normalizado (como o de
  `models/model_orders.py::get_order`, com itens, totais em sats, endereço já
  descriptografado, status). Gerar PDF com: nº do pedido + token, itens
  (nome/qtd/preço), total fiat E sats, status de pagamento, endereço de entrega,
  método de pagamento, e instruções de contato (WhatsApp/Telegram vindos do
  config, passados como parâmetro — NÃO ler segredos direto).
- Embutir um QR de acompanhamento usando `services/service_qr.py` (reuso).
- NÃO criar a rota de download nem tocar em `routes_checkout.py`/sessão/auth —
  isso é F-core (Opus). Apenas expor `build_order_pdf` + um teste.

## Reuso
- `service_qr.py` (QR), estrutura de `order` de `model_orders.py`.

## Restrições (AGENTS.md)
- NÃO tocar em pagamentos, checkout, auth/sessão, segredos, migrações, `main`,
  commits/PR. Só `service_pdf.py`, `requirements.txt` e o teste.
- Sem edições sobrepostas com outras fases.

## Aceite
- `python -m pytest tests/ -q` verde.
- Novo `tests/test_service_pdf.py`: dado um order dict de exemplo,
  `build_order_pdf` retorna bytes não-vazios começando com `%PDF`.
- Função pura e determinística (sem I/O de rede além do QR local em memória).
