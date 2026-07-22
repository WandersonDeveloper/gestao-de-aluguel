import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Upload, Trash2, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type {
  Equipment,
  EquipmentCategory,
  EquipmentPhoto,
  EquipmentStatus,
  EquipmentStock,
  Filial,
  InventoryMovement,
} from "@/types/api";
import { equipmentStatusLabels, equipmentStatusVariant, formatCurrency } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ALLOWED_TRANSITIONS: Record<EquipmentStatus, EquipmentStatus[]> = {
  disponivel: ["reservado", "manutencao"],
  reservado: ["alugado", "disponivel"],
  alugado: ["disponivel", "manutencao"],
  manutencao: ["disponivel"],
};

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

export function EquipmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const equipmentId = Number(id);
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { user } = useAuth();
  const canManage = user?.papel === "admin" || user?.papel === "operador";

  const [novoStatus, setNovoStatus] = useState<string>("");
  const [motivo, setMotivo] = useState("");

  const [stockDialogOpen, setStockDialogOpen] = useState(false);
  const [editingStock, setEditingStock] = useState<EquipmentStock | null>(null);
  const [stockForm, setStockForm] = useState<StockFormState>(emptyStockForm);

  const { data: equipment } = useQuery({
    queryKey: ["equipment", equipmentId],
    queryFn: async () => (await api.get<Equipment>(`/equipment/${equipmentId}`)).data,
    enabled: !!equipmentId,
  });

  const { data: categories } = useQuery({
    queryKey: ["equipment-categories"],
    queryFn: async () => (await api.get<EquipmentCategory[]>("/equipment-categories")).data,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  const { data: photos } = useQuery({
    queryKey: ["equipment", equipmentId, "photos"],
    queryFn: async () => (await api.get<EquipmentPhoto[]>(`/equipment/${equipmentId}/photos`)).data,
    enabled: !!equipmentId,
  });

  const { data: movements } = useQuery({
    queryKey: ["equipment", equipmentId, "movements"],
    queryFn: async () =>
      (await api.get<InventoryMovement[]>(`/equipment/${equipmentId}/movements`)).data,
    enabled: !!equipmentId,
  });

  const changeStatusMutation = useMutation({
    mutationFn: async () =>
      api.post(`/equipment/${equipmentId}/status`, { status: novoStatus, motivo: motivo || null }),
    onSuccess: () => {
      toast.success("Status atualizado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId] });
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId, "movements"] });
      setNovoStatus("");
      setMotivo("");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const uploadPhotoMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.post(`/equipment/${equipmentId}/photos`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      toast.success("Foto enviada com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId, "photos"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deletePhotoMutation = useMutation({
    mutationFn: async (key: string) => api.delete(`/equipment/${equipmentId}/photos/${key}`),
    onSuccess: () => {
      toast.success("Foto removida.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId, "photos"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

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
      closeStockDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteStockMutation = useMutation({
    mutationFn: async (filialId: number) => api.delete(`/equipment/${equipmentId}/estoque/${filialId}`),
    onSuccess: () => {
      toast.success("Estoque removido dessa filial.");
      queryClient.invalidateQueries({ queryKey: ["equipment", equipmentId] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openAddStockDialog() {
    setEditingStock(null);
    setStockForm(emptyStockForm);
    setStockDialogOpen(true);
  }

  function openEditStockDialog(stock: EquipmentStock) {
    setEditingStock(stock);
    setStockForm({
      filial_id: String(stock.filial_id),
      quantidade: String(stock.quantidade),
      valor_diario: stock.valor_diario ?? "",
      valor_mensal: stock.valor_mensal ?? "",
      valor_hora: stock.valor_hora ?? "",
    });
    setStockDialogOpen(true);
  }

  function closeStockDialog() {
    setStockDialogOpen(false);
    setEditingStock(null);
  }

  function handleStockSubmit(event: React.FormEvent) {
    event.preventDefault();
    const filialId = Number(stockForm.filial_id);
    setStockMutation.mutate({ filialId, payload: stockForm });
  }

  function handleDeleteStock(stock: EquipmentStock, filialNome: string) {
    if (window.confirm(`Remover o estoque desse equipamento na filial "${filialNome}"?`)) {
      deleteStockMutation.mutate(stock.filial_id);
    }
  }

  if (!equipment) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const categoryName = categories?.find((c) => c.id === equipment.categoria_id)?.nome ?? "—";
  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));
  const isEstoque = equipment.quantidade_total > 1 || equipment.estoques.length > 1;
  const possibleTransitions = ALLOWED_TRANSITIONS[equipment.status] ?? [];
  const filiaisDisponiveisParaAdicionar = (filiais ?? []).filter(
    (f) => !equipment.estoques.some((e) => e.filial_id === f.id),
  );

  return (
    <div>
      <Link to="/equipamentos" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Voltar para equipamentos
      </Link>

      <PageHeader
        title={equipment.nome}
        description={`${categoryName} · ${equipment.identificador ?? "sem identificador"}`}
        actions={<Badge variant={equipmentStatusVariant[equipment.status]}>{equipmentStatusLabels[equipment.status]}</Badge>}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dados do equipamento</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Marca</p>
              <p className="text-slate-900">{equipment.marca ?? "—"}</p>
            </div>
            <div>
              <p className="text-slate-500">Modelo</p>
              <p className="text-slate-900">{equipment.modelo ?? "—"}</p>
            </div>
            <div>
              <p className="text-slate-500">Quantidade total (todas as filiais)</p>
              <p className="text-slate-900">
                {equipment.quantidade_total}
                {isEstoque && " (item de estoque)"}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-slate-500">Localização</p>
              <p className="text-slate-900">{equipment.localizacao ?? "—"}</p>
            </div>
            <div className="col-span-2">
              <p className="text-slate-500">Observações</p>
              <p className="text-slate-900">{equipment.observacoes ?? "—"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alterar status</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {isEstoque ? (
              <p className="text-sm text-slate-500">
                Item de estoque (quantidade &gt; 1 ou em mais de uma filial): o status individual não se
                aplica — a disponibilidade é controlada pela quantidade reservada em cada contrato, por
                filial.
              </p>
            ) : !canManage ? (
              <p className="text-sm text-slate-500">Apenas admin/operador podem alterar o status.</p>
            ) : possibleTransitions.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhuma transição disponível.</p>
            ) : (
              <>
                <Select value={novoStatus} onValueChange={setNovoStatus}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o novo status" />
                  </SelectTrigger>
                  <SelectContent>
                    {possibleTransitions.map((status) => (
                      <SelectItem key={status} value={status}>
                        {equipmentStatusLabels[status]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Textarea
                  placeholder="Motivo (opcional)"
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                />
                <Button
                  disabled={!novoStatus || changeStatusMutation.isPending}
                  onClick={() => changeStatusMutation.mutate()}
                >
                  {changeStatusMutation.isPending ? "Aplicando..." : "Aplicar transição"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Estoque por filial</CardTitle>
            {canManage && filiaisDisponiveisParaAdicionar.length > 0 && (
              <Button size="sm" onClick={openAddStockDialog}>
                <Plus className="h-4 w-4" /> Adicionar filial
              </Button>
            )}
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filial</TableHead>
                  <TableHead>Quantidade</TableHead>
                  <TableHead>Valor diário</TableHead>
                  <TableHead>Valor mensal</TableHead>
                  <TableHead>Valor/hora</TableHead>
                  {canManage && <TableHead className="w-24 text-right">Ações</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {equipment.estoques.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={canManage ? 6 : 5} className="text-center text-slate-500">
                      Nenhum estoque cadastrado ainda — este equipamento não está disponível em nenhuma
                      filial.
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
                        <Button variant="ghost" size="icon" onClick={() => openEditStockDialog(estoque)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            handleDeleteStock(estoque, filiaisById.get(estoque.filial_id) ?? `Filial #${estoque.filial_id}`)
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
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fotos</CardTitle>
          </CardHeader>
          <CardContent>
            {canManage && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) uploadPhotoMutation.mutate(file);
                    e.target.value = "";
                  }}
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="mb-3"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadPhotoMutation.isPending}
                >
                  <Upload className="h-4 w-4" /> {uploadPhotoMutation.isPending ? "Enviando..." : "Enviar foto"}
                </Button>
              </>
            )}
            <div className="grid grid-cols-3 gap-2">
              {photos?.length === 0 && <p className="col-span-3 text-sm text-slate-500">Nenhuma foto.</p>}
              {photos?.map((photo) => (
                <div key={photo.key} className="group relative aspect-square overflow-hidden rounded-md border border-slate-200">
                  <img src={photo.url} alt="Foto do equipamento" className="h-full w-full object-cover" />
                  {canManage && (
                    <button
                      onClick={() => deletePhotoMutation.mutate(photo.key)}
                      className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Histórico de movimentação</CardTitle>
            <p className="text-xs text-slate-500">Últimos 30 dias</p>
          </CardHeader>
          <CardContent>
            <div className="max-h-80 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>De</TableHead>
                    <TableHead>Para</TableHead>
                    <TableHead>Motivo</TableHead>
                    <TableHead>Data</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {movements?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-slate-500">
                        Sem histórico nos últimos 30 dias.
                      </TableCell>
                    </TableRow>
                  )}
                  {movements?.map((movement) => (
                    <TableRow key={movement.id}>
                      <TableCell>{equipmentStatusLabels[movement.status_anterior]}</TableCell>
                      <TableCell>{equipmentStatusLabels[movement.status_novo]}</TableCell>
                      <TableCell>{movement.motivo ?? "—"}</TableCell>
                      <TableCell>{new Date(movement.created_at).toLocaleString("pt-BR")}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={stockDialogOpen} onOpenChange={setStockDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingStock ? "Editar estoque da filial" : "Adicionar estoque em filial"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleStockSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 flex flex-col gap-1.5">
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
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="quantidade">Quantidade nessa filial</Label>
                <Input
                  id="quantidade"
                  type="number"
                  min={1}
                  required
                  value={stockForm.quantidade}
                  onChange={(e) => setStockForm({ ...stockForm, quantidade: e.target.value })}
                />
                <p className="text-xs text-slate-500">
                  A mesma quantidade e os mesmos valores só valem para esta filial — outra filial pode ter
                  quantidade e preços diferentes para o mesmo equipamento.
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="valor_diario">Valor diário</Label>
                <Input
                  id="valor_diario"
                  type="number"
                  step="0.01"
                  value={stockForm.valor_diario}
                  onChange={(e) => setStockForm({ ...stockForm, valor_diario: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="valor_mensal">Valor mensal</Label>
                <Input
                  id="valor_mensal"
                  type="number"
                  step="0.01"
                  value={stockForm.valor_mensal}
                  onChange={(e) => setStockForm({ ...stockForm, valor_mensal: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="valor_hora">Valor por hora</Label>
                <Input
                  id="valor_hora"
                  type="number"
                  step="0.01"
                  value={stockForm.valor_hora}
                  onChange={(e) => setStockForm({ ...stockForm, valor_hora: e.target.value })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeStockDialog}>
                Cancelar
              </Button>
              <Button type="submit" disabled={setStockMutation.isPending || !stockForm.filial_id}>
                {setStockMutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
