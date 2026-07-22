import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { ContractWithItems, Equipment, Filial } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function ContractAddItemPage() {
  const { id } = useParams<{ id: string }>();
  const contractId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [quantidades, setQuantidades] = useState<Record<string, number>>({});
  const [condicaoCobranca, setCondicaoCobranca] = useState<string>("");
  const [dataVencimento, setDataVencimento] = useState("");
  const [motivo, setMotivo] = useState("");

  const { data: contract } = useQuery({
    queryKey: ["contracts", contractId],
    queryFn: async () => (await api.get<ContractWithItems>(`/contracts/${contractId}`)).data,
    enabled: !!contractId,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  const { data: availableEquipment } = useQuery({
    queryKey: ["equipment", "disponivel"],
    queryFn: async () =>
      (await api.get<Equipment[]>("/equipment", { params: { status: "disponivel", limit: 500 } })).data,
  });

  const addItemsMutation = useMutation({
    mutationFn: async () => {
      const itens = Object.entries(quantidades)
        .filter(([, quantidade]) => quantidade > 0)
        .map(([key, quantidade]) => {
          const [equipamentoId, filialId] = key.split(":").map(Number);
          return { equipamento_id: equipamentoId, filial_id: filialId, quantidade };
        });
      return api.post(`/contracts/${contractId}/add-items`, {
        itens,
        // O valor é sempre calculado automaticamente pelo backend a partir do
        // preço cadastrado no estoque — para contratos de cobrança "única",
        // que não têm taxa recorrente própria, é preciso escolher qual
        // condição usar (diária ou mensal); nos demais casos o backend usa a
        // periodicidade do próprio contrato e este campo é ignorado.
        condicao_cobranca_item: isUnica ? condicaoCobranca || null : null,
        data_vencimento_aditivo: dataVencimento || null,
        motivo: motivo || null,
      });
    },
    onSuccess: () => {
      toast.success(
        "Item adicionado ao contrato. Se o cliente tiver telefone cadastrado, uma confirmação foi enviada via WhatsApp.",
      );
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "amendments"] });
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "invoices"] });
      navigate(`/contratos/${contractId}`);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  if (!contract) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));
  const isUnica = contract.periodicidade_cobranca === "unica";
  // Uma linha por par (equipamento, filial) com estoque cadastrado — o mesmo
  // equipamento pode aparecer mais de uma vez, uma por filial onde existe.
  const equipamentoFilialRows = (availableEquipment ?? []).flatMap((equipment) =>
    equipment.estoques.map((estoque) => ({ equipment, estoque })),
  );
  const quantidadeSelecionada = Object.values(quantidades).some((quantidade) => quantidade > 0);

  function addItemKey(equipamentoId: number, filialId: number) {
    return `${equipamentoId}:${filialId}`;
  }

  function setQuantidade(equipamentoId: number, filialId: number, quantidade: number) {
    setQuantidades((prev) => ({
      ...prev,
      [addItemKey(equipamentoId, filialId)]: Math.max(0, quantidade),
    }));
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
        title={`Adicionar item ao contrato #${contract.id}`}
        description="Adiciona equipamento a este contrato já ativo (aditivo), sem precisar criar um contrato novo."
      />

      <div className="w-full max-w-2xl rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-slate-500">
            Se o cliente tiver telefone cadastrado, uma confirmação via WhatsApp será enviada — o aditivo só é
            considerado aceito depois que o cliente responder.
          </p>

          <div className="flex flex-col gap-1.5">
            <Label>Equipamento</Label>
            <div className="max-h-64 overflow-y-auto rounded-md border border-slate-200 p-2">
              {equipamentoFilialRows.length === 0 && (
                <p className="p-2 text-sm text-slate-500">Nenhum equipamento com estoque disponível.</p>
              )}
              {equipamentoFilialRows.map(({ equipment, estoque }) => (
                <div
                  key={addItemKey(equipment.id, estoque.filial_id)}
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
                    value={quantidades[addItemKey(equipment.id, estoque.filial_id)] ?? ""}
                    placeholder="0"
                    onChange={(e) => setQuantidade(equipment.id, estoque.filial_id, Number(e.target.value) || 0)}
                  />
                </div>
              ))}
            </div>
          </div>

          {isUnica ? (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="condicao_cobranca">Condição de cobrança do item</Label>
              <Select value={condicaoCobranca} onValueChange={setCondicaoCobranca}>
                <SelectTrigger id="condicao_cobranca" className="max-w-xs">
                  <SelectValue placeholder="Sem cobrança (incluso no valor do contrato)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="diaria">Diária</SelectItem>
                  <SelectItem value="mensal">Mensal</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">
                Este contrato é de cobrança única, sem taxa recorrente própria — escolha diária ou mensal para
                que o valor seja calculado automaticamente a partir do preço cadastrado no estoque do
                equipamento. Deixe em branco para adicionar sem gerar cobrança extra.
              </p>
            </div>
          ) : (
            <p className="max-w-xl rounded-md bg-slate-50 p-2 text-xs text-slate-600">
              O valor do aditivo é calculado automaticamente a partir do preço cadastrado no estoque do
              equipamento (diário/mensal), conforme a cobrança deste contrato.
            </p>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="data_vencimento">Vencimento da fatura do aditivo (opcional)</Label>
            <Input
              id="data_vencimento"
              type="date"
              className="max-w-xs"
              value={dataVencimento}
              onChange={(e) => setDataVencimento(e.target.value)}
            />
            <p className="text-xs text-slate-500">
              Se em branco, vence hoje. Só se aplica quando o aditivo gera cobrança.
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="motivo">Motivo (opcional)</Label>
            <Textarea id="motivo" className="max-w-xl" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => navigate(`/contratos/${contractId}`)}>
              Cancelar
            </Button>
            <Button
              onClick={() => addItemsMutation.mutate()}
              disabled={addItemsMutation.isPending || !quantidadeSelecionada}
            >
              {addItemsMutation.isPending ? "Adicionando..." : "Adicionar item"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
