import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { BillingPeriodicity, Client, Contract, ContractItemRequest, ContractType, Equipment, Filial } from "@/types/api";
import {
  contractStatusLabels,
  contractStatusVariant,
  contractTypeLabels,
  formatCurrency,
  formatDate,
} from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const assinaturaListaLabels: Record<string, string> = {
  aguardando_confirmacao: "Assinatura pendente",
  confirmado: "Assinado",
  recusado: "Assinatura recusada",
};

const assinaturaFiltroLabels: Record<string, string> = {
  nao_enviado: "Não enviado",
  aguardando_confirmacao: "Assinatura pendente",
  confirmado: "Assinado",
  recusado: "Assinatura recusada",
};

const assinaturaListaVariant: Record<string, "success" | "warning" | "destructive"> = {
  aguardando_confirmacao: "warning",
  confirmado: "success",
  recusado: "destructive",
};

type FormState = {
  cliente_id: string;
  data_inicio: string;
  data_fim: string;
  emAberto: boolean;
  tipo: ContractType;
  periodicidade_cobranca: BillingPeriodicity;
  valor_total: string;
  valor_recorrente: string;
  observacoes: string;
  // chave "equipamentoId:filialId" -> quantidade selecionada (o mesmo
  // equipamento pode ter estoque em várias filiais, cada uma reservada
  // independentemente).
  itens: Record<string, number>;
};

const emptyForm: FormState = {
  cliente_id: "",
  data_inicio: "",
  data_fim: "",
  emAberto: false,
  tipo: "locacao",
  periodicidade_cobranca: "unica",
  valor_total: "",
  valor_recorrente: "",
  observacoes: "",
  itens: {},
};

export function ContractsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.papel === "admin";
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [tipoFilter, setTipoFilter] = useState<string>("todos");
  const [clienteFilter, setClienteFilter] = useState<string>("todos");
  const [assinaturaFilter, setAssinaturaFilter] = useState<string>("todos");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: contracts, isLoading } = useQuery({
    queryKey: ["contracts", statusFilter, tipoFilter, clienteFilter, assinaturaFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (statusFilter !== "todos") params.status = statusFilter;
      if (tipoFilter !== "todos") params.tipo = tipoFilter;
      if (clienteFilter !== "todos") params.cliente_id = clienteFilter;
      if (assinaturaFilter !== "todos") params.assinatura_status = assinaturaFilter;
      return (await api.get<Contract[]>("/contracts", { params })).data;
    },
    // Enquanto algum contrato estiver aguardando resposta do cliente pelo
    // WhatsApp, atualiza sozinho — o webhook confirma em segundo plano.
    refetchInterval: (query) =>
      query.state.data?.some((c) => c.assinatura_status === "aguardando_confirmacao") ? 5000 : false,
  });

  const { data: clients } = useQuery({
    queryKey: ["clients", "all"],
    queryFn: async () => (await api.get<Client[]>("/clients", { params: { limit: 500 } })).data,
  });

  const { data: availableEquipment } = useQuery({
    queryKey: ["equipment", "disponivel"],
    queryFn: async () =>
      (await api.get<Equipment[]>("/equipment", { params: { status: "disponivel", limit: 500 } })).data,
    enabled: dialogOpen,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
    enabled: dialogOpen,
  });

  const clientsById = new Map((clients ?? []).map((c) => [c.id, c.nome]));
  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));
  const clientOptions = (clients ?? []).map((c) => ({
    value: String(c.id),
    label: c.nome,
    searchText: c.documento,
  }));

  // Uma linha por par (equipamento, filial) com estoque cadastrado — o mesmo
  // equipamento pode aparecer mais de uma vez, uma por filial onde existe.
  const equipamentoFilialRows = (availableEquipment ?? []).flatMap((equipment) =>
    equipment.estoques.map((estoque) => ({ equipment, estoque })),
  );

  function itemKey(equipamentoId: number, filialId: number) {
    return `${equipamentoId}:${filialId}`;
  }

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) => {
      const itens: ContractItemRequest[] = Object.entries(payload.itens)
        .filter(([, quantidade]) => quantidade > 0)
        .map(([key, quantidade]) => {
          const [equipamentoId, filialId] = key.split(":").map(Number);
          return { equipamento_id: equipamentoId, filial_id: filialId, quantidade };
        });
      const valorTotal =
        payload.emAberto || payload.periodicidade_cobranca === "hora" ? null : payload.valor_total.trim() || null;
      const valorRecorrente = payload.emAberto ? payload.valor_recorrente.trim() || null : null;
      return api.post("/contracts", {
        cliente_id: Number(payload.cliente_id),
        data_inicio: payload.data_inicio,
        data_fim: payload.emAberto ? null : payload.data_fim,
        tipo: payload.tipo,
        periodicidade_cobranca: payload.periodicidade_cobranca,
        valor_total: valorTotal,
        valor_recorrente: valorRecorrente,
        observacoes: payload.observacoes || null,
        itens,
      });
    },
    onSuccess: () => {
      toast.success("Contrato criado com sucesso (rascunho).");
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
      setDialogOpen(false);
      setForm(emptyForm);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/contracts/${id}`),
    onSuccess: () => {
      toast.success("Contrato excluído.");
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function handleDelete(contract: Contract) {
    if (window.confirm(`Excluir o contrato #${contract.id} (rascunho)? Essa ação não pode ser desfeita.`)) {
      deleteMutation.mutate(contract.id);
    }
  }

  function setQuantidade(equipamentoId: number, filialId: number, quantidade: number) {
    setForm((prev) => ({
      ...prev,
      itens: { ...prev.itens, [itemKey(equipamentoId, filialId)]: Math.max(0, quantidade) },
    }));
  }

  const itensSelecionados = Object.values(form.itens).filter((quantidade) => quantidade > 0).length;

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    createMutation.mutate(form);
  }

  return (
    <div>
      <PageHeader
        title="Contratos"
        description="Contratos de aluguel de equipamentos"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> Novo contrato
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {Object.entries(contractStatusLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={tipoFilter} onValueChange={setTipoFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os tipos</SelectItem>
            {Object.entries(contractTypeLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Combobox
          className="w-64"
          value={clienteFilter}
          onValueChange={setClienteFilter}
          placeholder="Todos os clientes"
          searchPlaceholder="Buscar por nome ou CNPJ/CPF..."
          options={[{ value: "todos", label: "Todos os clientes" }, ...clientOptions]}
        />
        <Select value={assinaturaFilter} onValueChange={setAssinaturaFilter}>
          <SelectTrigger className="w-56">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Assinatura: todas</SelectItem>
            {Object.entries(assinaturaFiltroLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Cliente</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Início</TableHead>
              <TableHead>Fim</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Valor total</TableHead>
              {isAdmin && <TableHead className="w-16 text-right">Ações</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={isAdmin ? 7 : 6} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && contracts?.length === 0 && (
              <TableRow>
                <TableCell colSpan={isAdmin ? 7 : 6} className="py-6 text-center text-slate-500">
                  Nenhum contrato encontrado.
                </TableCell>
              </TableRow>
            )}
            {contracts?.map((contract) => (
              <TableRow key={contract.id}>
                <TableCell className="font-medium text-slate-900">
                  <Link to={`/contratos/${contract.id}`} className="hover:underline">
                    {clientsById.get(contract.cliente_id) ?? `Cliente #${contract.cliente_id}`}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{contractTypeLabels[contract.tipo]}</Badge>
                </TableCell>
                <TableCell>{formatDate(contract.data_inicio)}</TableCell>
                <TableCell>
                  {contract.data_fim ? (
                    formatDate(contract.data_fim)
                  ) : (
                    <Badge variant="outline">Em aberto</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex flex-col items-start gap-1">
                    <Badge variant={contractStatusVariant[contract.status]}>
                      {contractStatusLabels[contract.status]}
                    </Badge>
                    {contract.assinatura_status !== "nao_enviado" && (
                      <Badge variant={assinaturaListaVariant[contract.assinatura_status]}>
                        {assinaturaListaLabels[contract.assinatura_status]}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell>{formatCurrency(contract.valor_total)}</TableCell>
                {isAdmin && (
                  <TableCell className="text-right">
                    {contract.status === "rascunho" && (
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(contract)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Novo contrato</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label>Cliente</Label>
                <Combobox
                  value={form.cliente_id}
                  onValueChange={(value) => setForm({ ...form, cliente_id: value })}
                  placeholder="Selecione um cliente"
                  searchPlaceholder="Buscar por nome ou CNPJ/CPF..."
                  options={clientOptions}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Tipo de contrato</Label>
                <Select value={form.tipo} onValueChange={(value) => setForm({ ...form, tipo: value as ContractType })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="locacao">Locação</SelectItem>
                    <SelectItem value="servico">Prestação de Serviço</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-500">
                  Define o modelo do contrato gerado em PDF (partes e cláusulas).
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="data_inicio">Data início</Label>
                <Input
                  id="data_inicio"
                  type="date"
                  required
                  value={form.data_inicio}
                  onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="data_fim">Data fim</Label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-600">
                    <input
                      type="checkbox"
                      checked={form.emAberto}
                      onChange={(e) => {
                        const emAberto = e.target.checked;
                        setForm({
                          ...form,
                          emAberto,
                          periodicidade_cobranca:
                            emAberto && form.periodicidade_cobranca === "unica"
                              ? "mensal"
                              : form.periodicidade_cobranca,
                        });
                      }}
                    />
                    Em aberto (sem data fim)
                  </label>
                </div>
                <Input
                  id="data_fim"
                  type="date"
                  required={!form.emAberto}
                  disabled={form.emAberto}
                  value={form.emAberto ? "" : form.data_fim}
                  onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Periodicidade de cobrança</Label>
                <Select
                  value={form.periodicidade_cobranca}
                  onValueChange={(value) => setForm({ ...form, periodicidade_cobranca: value as BillingPeriodicity })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {!form.emAberto && <SelectItem value="unica">Única</SelectItem>}
                    <SelectItem value="mensal">Mensal</SelectItem>
                    <SelectItem value="diaria">Diária</SelectItem>
                    <SelectItem value="hora">Hora máquina</SelectItem>
                  </SelectContent>
                </Select>
                {form.emAberto && (
                  <p className="text-xs text-slate-500">
                    Contrato em aberto não pode ser cobrado com periodicidade única.
                  </p>
                )}
              </div>
              {form.emAberto ? (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="valor_recorrente">Valor recorrente (por período)</Label>
                  <Input
                    id="valor_recorrente"
                    type="number"
                    step="0.01"
                    disabled={form.periodicidade_cobranca === "hora"}
                    value={form.periodicidade_cobranca === "hora" ? "" : form.valor_recorrente}
                    onChange={(e) => setForm({ ...form, valor_recorrente: e.target.value })}
                  />
                  <p className="text-xs text-slate-500">
                    {form.periodicidade_cobranca === "hora"
                      ? "Cobrança por hora: a fatura é calculada na baixa, a partir das horas trabalhadas informadas × valor/hora de cada equipamento."
                      : "Valor cobrado a cada período — o job diário gera a próxima fatura automaticamente enquanto o contrato estiver ativo."}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="valor_total">Valor total (opcional)</Label>
                  <Input
                    id="valor_total"
                    type="number"
                    step="0.01"
                    disabled={form.periodicidade_cobranca === "hora"}
                    value={form.periodicidade_cobranca === "hora" ? "" : form.valor_total}
                    onChange={(e) => setForm({ ...form, valor_total: e.target.value })}
                  />
                  <p className="text-xs text-slate-500">
                    {form.periodicidade_cobranca === "hora"
                      ? "Cobrança por hora: a fatura é calculada na baixa, a partir das horas trabalhadas informadas × valor/hora de cada equipamento."
                      : "Sem valor, nenhuma fatura é gerada automaticamente."}
                  </p>
                </div>
              )}

              <div className="col-span-2 flex flex-col gap-1.5">
                <Label>Equipamentos disponíveis</Label>
                <div className="max-h-52 overflow-y-auto rounded-md border border-slate-200 p-2">
                  {equipamentoFilialRows.length === 0 && (
                    <p className="text-sm text-slate-500">
                      Nenhum equipamento com estoque cadastrado em alguma filial.
                    </p>
                  )}
                  {equipamentoFilialRows.map(({ equipment, estoque }) => (
                    <div
                      key={itemKey(equipment.id, estoque.filial_id)}
                      className="flex items-center justify-between gap-2 rounded px-1 py-1 text-sm hover:bg-slate-50"
                    >
                      <span>
                        {equipment.nome} {equipment.identificador ? `(${equipment.identificador})` : ""}
                        <span className="ml-1 text-xs text-slate-500">
                          — {filiaisById.get(estoque.filial_id) ?? `Filial #${estoque.filial_id}`} (estoque:{" "}
                          {estoque.quantidade})
                        </span>
                      </span>
                      <Input
                        type="number"
                        min={0}
                        max={estoque.quantidade}
                        className="w-20"
                        value={form.itens[itemKey(equipment.id, estoque.filial_id)] ?? ""}
                        placeholder="0"
                        onChange={(e) => setQuantidade(equipment.id, estoque.filial_id, Number(e.target.value) || 0)}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="observacoes">Observações</Label>
                <Textarea
                  id="observacoes"
                  value={form.observacoes}
                  onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || !form.cliente_id || itensSelecionados === 0}
              >
                {createMutation.isPending ? "Salvando..." : "Criar contrato"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
