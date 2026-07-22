export type ClientType = "PF" | "PJ";

export interface Client {
  id: number;
  nome: string;
  tipo: ClientType;
  documento: string;
  telefone: string | null;
  email: string | null;
  endereco: string | null;
  observacoes: string | null;
  created_at: string;
}

export interface EquipmentCategory {
  id: number;
  nome: string;
  descricao: string | null;
  created_at: string;
}

export type EquipmentStatus = "disponivel" | "reservado" | "alugado" | "manutencao";

export interface Filial {
  id: number;
  nome: string;
  endereco: string | null;
  telefone: string | null;
  observacoes: string | null;
  created_at: string;
}

export interface EquipmentStock {
  id: number;
  equipamento_id: number;
  filial_id: number;
  quantidade: number;
  valor_diario: string | null;
  valor_mensal: string | null;
  valor_hora: string | null;
}

export interface EquipmentStockUpsert {
  quantidade: number;
  valor_diario: string | null;
  valor_mensal: string | null;
  valor_hora: string | null;
}

export interface Equipment {
  id: number;
  nome: string;
  categoria_id: number;
  marca: string | null;
  modelo: string | null;
  identificador: string | null;
  status: EquipmentStatus;
  quantidade_total: number;
  estoques: EquipmentStock[];
  localizacao: string | null;
  observacoes: string | null;
  atributos_extra: Record<string, unknown>;
  foto_principal_url: string | null;
  created_at: string;
}

export interface EquipmentPhoto {
  key: string;
  url: string;
}

export interface InventoryMovement {
  id: number;
  equipamento_id: number;
  usuario_id: number;
  status_anterior: EquipmentStatus;
  status_novo: EquipmentStatus;
  motivo: string | null;
  created_at: string;
}

export interface Supplier {
  id: number;
  nome: string;
  documento: string | null;
  telefone: string | null;
  email: string | null;
  endereco: string | null;
  observacoes: string | null;
  created_at: string;
}

export type ContractStatus = "rascunho" | "ativo" | "vencido" | "encerrado" | "cancelado";
export type BillingPeriodicity = "unica" | "mensal" | "diaria" | "hora";
export type ContractItemStatus = "ativo" | "devolvido";
export type ContractType = "locacao" | "servico";
export type ContractSignatureStatus = "nao_enviado" | "aguardando_confirmacao" | "confirmado" | "recusado";

export interface ContractItem {
  id: number;
  contrato_id: number;
  equipamento_id: number;
  filial_id: number;
  data_inicio_item: string;
  /** null = item de contrato em aberto, sem data de término definida. */
  data_fim_item: string | null;
  quantidade: number;
  status: ContractItemStatus;
  valor_item: string | null;
  horas_trabalhadas: string | null;
}

export interface ContractItemRequest {
  equipamento_id: number;
  filial_id: number;
  quantidade: number;
}

export interface Contract {
  id: number;
  cliente_id: number;
  data_inicio: string;
  /** null = contrato em aberto, sem data de término definida. */
  data_fim: string | null;
  status: ContractStatus;
  tipo: ContractType;
  periodicidade_cobranca: BillingPeriodicity;
  valor_total: string | null;
  /** Valor cobrado a cada período, usado só quando data_fim é null. */
  valor_recorrente: string | null;
  observacoes: string | null;
  assinatura_status: ContractSignatureStatus;
  assinatura_confirmada_em: string | null;
  assinatura_resposta_texto: string | null;
  created_at: string;
}

export interface ContractWithItems extends Contract {
  itens: ContractItem[];
}

export type ContractAmendmentType = "extensao" | "baixa_total" | "baixa_parcial" | "cancelamento" | "adicao_item";

export interface ContractAmendment {
  id: number;
  contrato_id: number;
  usuario_id: number;
  tipo: ContractAmendmentType;
  data_anterior: string | null;
  data_nova: string | null;
  motivo: string | null;
  created_at: string;
  assinatura_status: ContractSignatureStatus;
  assinatura_resposta_texto: string | null;
  assinatura_confirmada_em: string | null;
  itens: ContractItem[];
}

export type ServiceOrderType = "preventiva" | "corretiva";
export type ServiceOrderPriority = "baixa" | "media" | "alta";
export type ServiceOrderStatus = "aberta" | "em_andamento" | "concluida" | "cancelada";

export interface ServiceOrder {
  id: number;
  equipamento_id: number;
  contrato_id: number | null;
  tipo: ServiceOrderType;
  descricao: string;
  prioridade: ServiceOrderPriority;
  status: ServiceOrderStatus;
  observacoes: string | null;
  data_abertura: string;
  data_conclusao: string | null;
}

export type InvoiceStatus = "pendente" | "paga" | "atrasada" | "cancelada";

export interface Invoice {
  id: number;
  contrato_id: number;
  data_vencimento: string;
  valor: string;
  status: InvoiceStatus;
  multa_juros_aplicado: string | null;
  numero_nota_fiscal: string | null;
  created_at: string;
}

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  contract_item_id: number;
  valor: string;
}

export interface Payment {
  id: number;
  invoice_id: number;
  usuario_id: number;
  valor: string;
  forma_pagamento: string | null;
  observacoes: string | null;
  created_at: string;
}

export type UserRoleValue = "admin" | "operador" | "financeiro";

export interface AppUser {
  id: number;
  nome: string;
  email: string;
  papel: UserRoleValue;
  ativo: boolean;
  created_at: string;
}

export interface RentalReport {
  total_contratos: number;
  contratos_rascunho: number;
  contratos_ativos: number;
  contratos_vencidos: number;
  contratos_encerrados: number;
  contratos_cancelados: number;
  valor_total_contratado: string;
}

export interface MostRentedEquipmentEntry {
  equipamento_id: number;
  equipamento_nome: string;
  quantidade_locacoes: number;
}

export interface OverdueInvoiceEntry {
  invoice_id: number;
  contrato_id: number;
  data_vencimento: string;
  valor: string;
  multa_juros_aplicado: string | null;
}

export interface OverdueByClientEntry {
  cliente_id: number;
  cliente_nome: string;
  quantidade_faturas: number;
  total_atrasado: string;
  faturas: OverdueInvoiceEntry[];
}

export interface DashboardReport {
  equipamentos_total: number;
  equipamentos_disponiveis: number;
  equipamentos_reservados: number;
  equipamentos_alugados: number;
  equipamentos_manutencao: number;
  contratos_ativos: number;
  contratos_vencidos: number;
  ordens_servico_abertas: number;
  faturas_atrasadas_quantidade: number;
  faturas_atrasadas_valor_total: string;
  receita_recebida_mes_atual: string;
}

export type MessageTemplateKey =
  | "cobranca_fatura"
  | "contrato_assinatura"
  | "aceite_confirmado"
  | "aceite_recusado"
  | "aditivo_confirmacao"
  | "aditivo_aceite_confirmado"
  | "aditivo_aceite_recusado";

export interface MessageTemplate {
  chave: MessageTemplateKey;
  conteudo: string;
  updated_at: string;
}

export type WhatsappConnectionState = "open" | "connecting" | "close" | null;

export interface WhatsappStatus {
  existe: boolean;
  estado: WhatsappConnectionState;
}

export interface WhatsappConnectResult {
  estado: WhatsappConnectionState;
  qrcode_base64: string | null;
}
