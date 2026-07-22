import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { Equipment, EquipmentStock, Filial } from "@/types/api";
import { formatCurrency } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type StockFormState = {
  filial_id: string;
  quantidade: string;
  valor_diario: string;
  valor_mensal: string;
  valor_hora: string;
};

const emptyStockForm: StockFormState = {
  filial_id: "",
  quantidade: "1",
  valor_diario: "",
  valor_mensal: "",
  valor_hora: "",
};

export function EquipmentStockPage() {
  const { id } = useParams<{ id: string }>();
  const equipmentId = Number(id);
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = user?.papel === "admin" || user?.papel === "operador";

  const [tab, setTab] = useState<"ver" | "adicionar">("ver");
  const [editingStock, setEditingStock] = useState<EquipmentStock | null>(null);
  const [stockForm, setStockForm] = useState<StockFormState>(emptyStockForm);

  const { data: equipment } = useQuery({
    queryKey: ["equipment", equipmentId],
    queryFn: async () => (await api.get<Equipment>(`/equipment/${equipmentId}`)).data,
    enabled: !!equipmentId,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));

  const setStockMutation = useMutation({
    mutationFn: async ({ filialId, payload }: { filialId: number; payload: StockFormState }) =>
      api.put(`/equipment/${equipmentId}/estoque/${filialId}`, {
        quantidade: Number(payload.quantidade) || 1,
        valor_diario: payload.valor_diario || null,
        valor_mensal: payload.valor_mensal || null,
        valor_hora: payload.valor_hora || null,
      }),
    onSuccess: () => {
      toast.success("Estoque da filial atualizado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId] });
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
      setEditingStock(null);
      setStockForm(emptyStockForm);
      setTab("ver");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteStockMutation = useMutation({
    mutationFn: async (filialId: number) => api.delete(`/equipment/${equipmentId}/estoque/${filialId}`),
    onSuccess: () => {
      toast.success("Estoque removido dessa filial.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId] });
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openAddStockTab() {
    setEditingStock(null);
    setStockForm(emptyStockForm);
    setTab("adicionar");
  }

  function openEditStockTab(stock: EquipmentStock) {
    setEditingStock(stock);
    setStockForm({
      filial_id: String(stock.filial_id),
      quantidade: String(stock.quantidade),
      valor_diario: stock.valor_diario ?? "",
      valor_mensal: stock.valor_mensal ?? "",
      valor_hora: stock.valor_hora ?? "",
    });
    setTab("adicionar");
  }

  function handleStockSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStockMutation.mutate({ filialId: Number(stockForm.filial_id), payload: stockForm });
  }

  function handleDeleteStock(stock: EquipmentStock, filialNome: string) {
    if (window.confirm(`Remover o estoque desse equipamento na filial "${filialNome}"?`)) {
      deleteStockMutation.mutate(stock.filial_id);
    }
  }

  if (!equipment) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const filiaisDisponiveisParaAdicionar = (filiais ?? []).filter(
    (f) => !equipment.estoques.some((e) => e.filial_id === f.id),
  );

  return (
    <div>
      <Link
        to={`/equipamentos/${equipmentId}`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" /> Voltar para {equipment.nome}
      </Link>

      <PageHeader
        title={`Estoque por filial — ${equipment.nome}`}
        description={`Total em todas as filiais: ${equipment.quantidade_total}`}
      />

      <Tabs value={tab} onValueChange={(value) => setTab(value as "ver" | "adicionar")}>
        <TabsList>
          <TabsTrigger value="ver">Ver estoque</TabsTrigger>
          {canManage && (
            <TabsTrigger value="adicionar" onClick={() => !editingStock && openAddStockTab()}>
              Adicionar produto em estoque
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="ver">
          <div className="rounded-lg border border-slate-200 bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filial</TableHead>
                  <TableHead>Quantidade</TableHead>
                  <TableHead>Valor diário</TableHead>
                  <TableHead>Valor mensal</TableHead>
                  <TableHead>Valor/hora</TableHead>
                  {canManage && <TableHead className="w-20 text-right">Ações</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {equipment.estoques.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={canManage ? 6 : 5} className="py-6 text-center text-slate-500">
                      Nenhum estoque cadastrado ainda.
                    </TableCell>
                  </TableRow>
                )}
                {equipment.estoques.map((estoque) => (
                  <TableRow key={estoque.id}>
                    <TableCell className="font-medium text-slate-900">
                      {filiaisById.get(estoque.filial_id) ?? `Filial #${estoque.filial_id}`}
                    </TableCell>
                    <TableCell>{estoque.quantidade}</TableCell>
                    <TableCell>{formatCurrency(estoque.valor_diario)}</TableCell>
                    <TableCell>{formatCurrency(estoque.valor_mensal)}</TableCell>
                    <TableCell>{formatCurrency(estoque.valor_hora)}</TableCell>
                    {canManage && (
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => openEditStockTab(estoque)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            handleDeleteStock(
                              estoque,
                              filiaisById.get(estoque.filial_id) ?? `Filial #${estoque.filial_id}`,
                            )
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {canManage && (
          <TabsContent value="adicionar">
            <div className="w-full rounded-lg border border-slate-200 bg-white p-6">
              <form onSubmit={handleStockSubmit} className="flex flex-col gap-4">
                <p className="text-sm font-medium text-slate-900">
                  {editingStock ? "Editar estoque da filial" : "Adicionar estoque em filial"}
                </p>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <div className="flex flex-col gap-1.5 lg:col-span-1">
                    <Label>Filial</Label>
                    <Select
                      value={stockForm.filial_id}
                      onValueChange={(value) => setStockForm({ ...stockForm, filial_id: value })}
                      disabled={!!editingStock}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione a filial" />
                      </SelectTrigger>
                      <SelectContent>
                        {(editingStock ? filiais ?? [] : filiaisDisponiveisParaAdicionar).map((filial) => (
                          <SelectItem key={filial.id} value={String(filial.id)}>
                            {filial.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="stock_quantidade">Quantidade</Label>
                    <Input
                      id="stock_quantidade"
                      type="number"
                      min={1}
                      required
                      value={stockForm.quantidade}
                      onChange={(e) => setStockForm({ ...stockForm, quantidade: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="stock_valor_diario">Valor diário</Label>
                    <Input
                      id="stock_valor_diario"
                      type="number"
                      step="0.01"
                      value={stockForm.valor_diario}
                      onChange={(e) => setStockForm({ ...stockForm, valor_diario: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="stock_valor_mensal">Valor mensal</Label>
                    <Input
                      id="stock_valor_mensal"
                      type="number"
                      step="0.01"
                      value={stockForm.valor_mensal}
                      onChange={(e) => setStockForm({ ...stockForm, valor_mensal: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="stock_valor_hora">Valor por hora</Label>
                    <Input
                      id="stock_valor_hora"
                      type="number"
                      step="0.01"
                      value={stockForm.valor_hora}
                      onChange={(e) => setStockForm({ ...stockForm, valor_hora: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  {editingStock && (
                    <Button type="button" variant="outline" onClick={openAddStockTab}>
                      Cancelar edição
                    </Button>
                  )}
                  <Button type="submit" disabled={setStockMutation.isPending || !stockForm.filial_id}>
                    {setStockMutation.isPending ? "Salvando..." : editingStock ? "Salvar alterações" : "Adicionar"}
                  </Button>
                </div>
              </form>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
