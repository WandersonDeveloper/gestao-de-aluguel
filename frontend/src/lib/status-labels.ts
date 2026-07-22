export const equipmentStatusLabels: Record<string, string> = {
  disponivel: "Disponível",
  reservado: "Reservado",
  alugado: "Alugado",
  manutencao: "Manutenção",
};

export const equipmentStatusVariant: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
  disponivel: "success",
  reservado: "warning",
  alugado: "secondary",
  manutencao: "destructive",
};

export const contractStatusLabels: Record<string, string> = {
  rascunho: "Rascunho",
  ativo: "Ativo",
  vencido: "Vencido",
  encerrado: "Encerrado",
  cancelado: "Cancelado",
};

export const contractStatusVariant: Record<string, "success" | "warning" | "secondary" | "destructive" | "outline"> = {
  rascunho: "outline",
  ativo: "success",
  vencido: "warning",
  encerrado: "secondary",
  cancelado: "destructive",
};

export const contractTypeLabels: Record<string, string> = {
  locacao: "Locação",
  servico: "Prestação de Serviço",
};

export const contractSignatureStatusLabels: Record<string, string> = {
  nao_enviado: "Assinatura não enviada",
  aguardando_confirmacao: "Aguardando confirmação",
  confirmado: "Assinatura confirmada",
  recusado: "Assinatura recusada",
};

export const contractSignatureStatusVariant: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
  nao_enviado: "secondary",
  aguardando_confirmacao: "warning",
  confirmado: "success",
  recusado: "destructive",
};

export const serviceOrderStatusLabels: Record<string, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

export const serviceOrderStatusVariant: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
  aberta: "warning",
  em_andamento: "secondary",
  concluida: "success",
  cancelada: "destructive",
};

export const invoiceStatusLabels: Record<string, string> = {
  pendente: "Pendente",
  paga: "Paga",
  atrasada: "Atrasada",
  cancelada: "Cancelada",
};

export const invoiceStatusVariant: Record<string, "success" | "warning" | "secondary" | "destructive"> = {
  pendente: "secondary",
  paga: "success",
  atrasada: "destructive",
  cancelada: "warning",
};

export function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  return numeric.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const [year, month, day] = value.split("T")[0].split("-");
  return `${day}/${month}/${year}`;
}
