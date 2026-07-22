import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { ContractWithItems, Equipment, Invoice, Payment } from "@/types/api";
import { formatCurrency, formatDate, invoiceStatusLabels, invoiceStatusVariant } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function ContractBaixaPage() {
  const { id } = useParams<{ id: string }>();
  const contractId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManagePayments = user?.papel === "admin" || user?.papel === "financeiro";

  const [itemIds, setItemIds] = useState<number[]>([]);
  const [motivo, setMotivo] = useState("");
  const [horas, setHoras] = useState<Record<number, string>>({});
  const [faturaIdsSelecionadas, setFaturaIdsSelecionadas] = useState<number[]>([]);

  const { data: contract } = useQuery({
    queryKey: ["contracts", contractId],
    queryFn: async () => (await api.get<ContractWithItems>(`/contracts/${contractId}`)).data,
    enabled: !!contractId,
  });

  const { data: equipmentList } = useQuery({
    queryKey: ["equipment", "all"],
    queryFn: async () => (await api.get<Equipment[]>("/equipment", { params: { limit: 500 } })).data,
  });

  const { data: invoices } = useQuery({
    queryKey: ["contracts", contractId, "invoices"],
    queryFn: async () => (await api.get<Invoice[]>("/invoices", { params: { contrato_id: contractId } })).data,
    enabled: !!contractId,
  });

  const invalidateContract = () => {
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "amendments"] });
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "invoices"] });
  };

  const baixaMutation = useMutation({
    mutationFn: async () => {
      const horas_por_item =
        contract?.periodicidade_cobranca === "hora"
          ? Object.fromEntries(
              Object.entries(horas)
                .filter(([, valor]) => valor.trim() !== "")
                .map(([itemId, valor]) => [itemId, valor]),
            )
          : undefined;
      return api.post(`/contracts/${contractId}/baixa`, {
        item_ids: itemIds.length > 0 ? itemIds : null,
        motivo: motivo || null,
        horas_por_item,
      });
    },
    onSuccess: () => {
      toast.success("Baixa registrada com sucesso.");
      invalidateContract();
      navigate(`/contratos/${contractId}`);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const quitarFaturasMutation = useMutation({
    mutationFn: async () => {
      for (const faturaId of faturaIdsSelecionadas) {
        const fatura = invoices?.find((f) => f.id === faturaId);
        if (!fatura) continue;
        const payments = (await api.get<Payment[]>(`/invoices/${faturaId}/payments`)).data;
        const totalPago = payments.reduce((sum, p) => sum + Number(p.valor), 0);
        const restante = Number(fatura.valor) - totalPago;
        if (restante > 0) {
          await api.post(`/invoices/${faturaId}/payments`, {
            valor: restante.toFixed(2),
            observacoes: "Quitação registrada ao dar baixa no contrato",
          });
        }
      }
    },
    onSuccess: () => {
      toast.success("Fatura(s) quitada(s) com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "invoices"] });
      setFaturaIdsSelecionadas([]);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  if (!contract) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const equipmentById = new Map((equipmentList ?? []).map((e) => [e.id, e]));
  const activeItems = contract.itens.filter((item) => item.status === "ativo");
  const isHourly = contract.periodicidade_cobranca === "hora";
  const itensParaBaixa = itemIds.length > 0 ? activeItems.filter((i) => itemIds.includes(i.id)) : activeItems;
  const isBaixaTotal = itemIds.length === 0;
  const faturasEmAberto = (invoices ?? []).filter((f) => f.status === "pendente" || f.status === "atrasada");
  const somaFaturasSelecionadas = faturasEmAberto
    .filter((f) => faturaIdsSelecionadas.includes(f.id))
    .reduce((sum, f) => sum + Number(f.valor), 0);
  const baixaValido =
    (!isHourly || itensParaBaixa.every((item) => Number(horas[item.id] ?? "") > 0)) &&
    (!isBaixaTotal || faturasEmAberto.length === 0);

  function toggleItem(itemId: number) {
    setItemIds((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]));
  }

  function toggleFatura(faturaId: number) {
    setFaturaIdsSelecionadas((prev) =>
      prev.includes(faturaId) ? prev.filter((id) => id !== faturaId) : [...prev, faturaId],
    );
  }

  return (
    <div>
      <Link
        to={`/contratos/${contractId}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" /> Voltar para o contrato
      </Link>

      <PageHeader
        title={`Dar baixa no contrato #${contract.id}`}
        description="Selecione os itens para baixa parcial, ou deixe tudo desmarcado para dar baixa total."
      />

      <div className="w-full max-w-2xl rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-col gap-4">
          {isHourly && (
            <p className="rounded-md bg-amber-50 p-2 text-xs text-amber-800">
              Contrato cobrado por hora: informe as horas trabalhadas de cada item — a fatura é calculada
              agora, na baixa.
            </p>
          )}

          <div className="flex flex-col gap-1.5">
            <Label>Itens do contrato</Label>
            <div className="max-h-64 overflow-y-auto rounded-md border border-slate-200 p-2">
              {activeItems.map((item) => (
                <div key={item.id} className="flex items-center gap-2 rounded px-1 py-1.5 text-sm hover:bg-slate-50">
                  <label className="flex flex-1 items-center gap-2">
                    <input type="checkbox" checked={itemIds.includes(item.id)} onChange={() => toggleItem(item.id)} />
                    {equipmentById.get(item.equipamento_id)?.nome ?? `#${item.equipamento_id}`}
                  </label>
                  {isHourly && (
                    <Input
                      type="number"
                      step="0.5"
                      min="0"
                      placeholder="horas"
                      className="w-24"
                      value={horas[item.id] ?? ""}
                      onChange={(e) => setHoras((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {isBaixaTotal && faturasEmAberto.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-2">
              <p className="mb-2 text-xs text-amber-800">
                Baixa total exige as faturas em aberto quitadas ou canceladas. Selecione abaixo as que deseja
                quitar agora.
              </p>
              <div className="flex flex-col gap-1">
                {faturasEmAberto.map((fatura) => (
                  <label key={fatura.id} className="flex items-center gap-2 rounded px-1 py-1 text-sm hover:bg-white">
                    <input
                      type="checkbox"
                      checked={faturaIdsSelecionadas.includes(fatura.id)}
                      onChange={() => toggleFatura(fatura.id)}
                    />
                    Fatura #{fatura.id} — vencimento {formatDate(fatura.data_vencimento)} —{" "}
                    {formatCurrency(fatura.valor)}
                    <Badge variant={invoiceStatusVariant[fatura.status]}>{invoiceStatusLabels[fatura.status]}</Badge>
                  </label>
                ))}
              </div>
              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-amber-800">
                  Total selecionado: <strong>{formatCurrency(somaFaturasSelecionadas)}</strong>
                </p>
                {canManagePayments ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => quitarFaturasMutation.mutate()}
                    disabled={quitarFaturasMutation.isPending || faturaIdsSelecionadas.length === 0}
                  >
                    {quitarFaturasMutation.isPending ? "Quitando..." : "Quitar faturas selecionadas"}
                  </Button>
                ) : (
                  <p className="text-xs text-slate-500">Apenas admin/financeiro pode quitar faturas.</p>
                )}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="baixa_motivo">Motivo (opcional)</Label>
            <Textarea id="baixa_motivo" className="max-w-xl" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => navigate(`/contratos/${contractId}`)}>
              Cancelar
            </Button>
            <Button
              onClick={() => baixaMutation.mutate()}
              disabled={baixaMutation.isPending || !baixaValido}
              title={
                isBaixaTotal && faturasEmAberto.length > 0
                  ? "Quite ou cancele as faturas em aberto antes de confirmar a baixa total"
                  : undefined
              }
            >
              {baixaMutation.isPending ? "Registrando..." : "Confirmar baixa"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
