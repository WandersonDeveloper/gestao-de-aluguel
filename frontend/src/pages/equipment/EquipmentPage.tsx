import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Trash2, Boxes, ImageOff } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { Equipment, EquipmentCategory, Filial } from "@/types/api";
import { equipmentStatusLabels, equipmentStatusVariant } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type FormState = {
  nome: string;
  categoria_id: string;
  marca: string;
  modelo: string;
  identificador: string;
  localizacao: string;
  observacoes: string;
};

const emptyForm: FormState = {
  nome: "",
  categoria_id: "",
  marca: "",
  modelo: "",
  identificador: "",
  localizacao: "",
  observacoes: "",
};

export function EquipmentPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = user?.papel === "admin" || user?.papel === "operador";
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Equipment | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: categories } = useQuery({
    queryKey: ["equipment-categories"],
    queryFn: async () => (await api.get<EquipmentCategory[]>("/equipment-categories")).data,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  const { data: equipmentList, isLoading } = useQuery({
    queryKey: ["equipment", search, statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (search) params.nome = search;
      if (statusFilter !== "todos") params.status = statusFilter;
      return (await api.get<Equipment[]>("/equipment", { params })).data;
    },
  });

  const categoriesById = new Map((categories ?? []).map((c) => [c.id, c.nome]));
  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));

  function toApiPayload(payload: FormState) {
    return {
      nome: payload.nome,
      categoria_id: Number(payload.categoria_id),
      marca: payload.marca || null,
      modelo: payload.modelo || null,
      identificador: payload.identificador || null,
      localizacao: payload.localizacao || null,
      observacoes: payload.observacoes || null,
    };
  }

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) => api.post("/equipment", toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Equipamento cadastrado com sucesso. Agora defina o estoque por filial na tela de detalhe.");
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: FormState }) =>
      api.patch(`/equipment/${id}`, toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Equipamento atualizado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/equipment/${id}`),
    onSuccess: () => {
      toast.success("Equipamento removido.");
      queryClient.invalidateQueries({ queryKey: ["equipment"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openCreateDialog() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(equipment: Equipment) {
    setEditing(equipment);
    setForm({
      nome: equipment.nome,
      categoria_id: String(equipment.categoria_id),
      marca: equipment.marca ?? "",
      modelo: equipment.modelo ?? "",
      identificador: equipment.identificador ?? "",
      localizacao: equipment.localizacao ?? "",
      observacoes: equipment.observacoes ?? "",
    });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  function handleDelete(equipment: Equipment) {
    if (window.confirm(`Excluir o equipamento "${equipment.nome}"?`)) {
      deleteMutation.mutate(equipment.id);
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: form });
    } else {
      createMutation.mutate(form);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  function estoquesResumo(equipment: Equipment) {
    if (equipment.estoques.length === 0) return "Sem estoque cadastrado";
    return equipment.estoques
      .map((e) => `${filiaisById.get(e.filial_id) ?? `Filial #${e.filial_id}`}: ${e.quantidade}`)
      .join(" · ");
  }

  return (
    <div>
      <PageHeader
        title="Equipamentos"
        description="Cadastro dos equipamentos — a quantidade e os valores de cada um são definidos por filial na tela de detalhe"
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4" /> Novo equipamento
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <div className="relative w-72">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Buscar por nome..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {Object.entries(equipmentStatusLabels).map(([value, label]) => (
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
              <TableHead className="w-16">Foto</TableHead>
              <TableHead>Nome</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Identificador</TableHead>
              <TableHead>Estoque por filial</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-24 text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={8} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && equipmentList?.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="py-6 text-center text-slate-500">
                  Nenhum equipamento encontrado.
                </TableCell>
              </TableRow>
            )}
            {equipmentList?.map((equipment) => (
              <TableRow key={equipment.id} className="cursor-pointer">
                <TableCell>
                  <Link to={`/equipamentos/${equipment.id}`}>
                    {equipment.foto_principal_url ? (
                      <img
                        src={equipment.foto_principal_url}
                        alt={equipment.nome}
                        className="h-10 w-10 rounded-md border border-slate-200 object-cover"
                      />
                    ) : (
                      <div className="flex h-10 w-10 items-center justify-center rounded-md border border-dashed border-slate-200 text-slate-300">
                        <ImageOff className="h-4 w-4" />
                      </div>
                    )}
                  </Link>
                </TableCell>
                <TableCell className="font-medium text-slate-900">
                  <Link to={`/equipamentos/${equipment.id}`} className="hover:underline">
                    {equipment.nome}
                  </Link>
                </TableCell>
                <TableCell>{categoriesById.get(equipment.categoria_id) ?? "—"}</TableCell>
                <TableCell>{equipment.identificador ?? "—"}</TableCell>
                <TableCell className="max-w-64 truncate text-sm text-slate-600" title={estoquesResumo(equipment)}>
                  {estoquesResumo(equipment)}
                </TableCell>
                <TableCell className="font-medium text-slate-900">{equipment.quantidade_total}</TableCell>
                <TableCell>
                  <Badge variant={equipmentStatusVariant[equipment.status]}>
                    {equipmentStatusLabels[equipment.status]}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" title="Estoque por filial" asChild>
                    <Link to={`/equipamentos/${equipment.id}/estoque`}>
                      <Boxes className="h-4 w-4" />
                    </Link>
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => openEditDialog(equipment)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  {canManage && (
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(equipment)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Editar equipamento" : "Novo equipamento"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="nome">Nome</Label>
                <Input
                  id="nome"
                  required
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label>Categoria</Label>
                <Select
                  value={form.categoria_id}
                  onValueChange={(value) => setForm({ ...form, categoria_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione uma categoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories?.map((category) => (
                      <SelectItem key={category.id} value={String(category.id)}>
                        {category.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="marca">Marca</Label>
                <Input
                  id="marca"
                  value={form.marca}
                  onChange={(e) => setForm({ ...form, marca: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="modelo">Modelo</Label>
                <Input
                  id="modelo"
                  value={form.modelo}
                  onChange={(e) => setForm({ ...form, modelo: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="identificador">Identificador (placa/chassi)</Label>
                <Input
                  id="identificador"
                  value={form.identificador}
                  onChange={(e) => setForm({ ...form, identificador: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="localizacao">Localização (referência livre)</Label>
                <Input
                  id="localizacao"
                  value={form.localizacao}
                  onChange={(e) => setForm({ ...form, localizacao: e.target.value })}
                />
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
            {!editing && (
              <p className="text-xs text-slate-500">
                Após salvar, defina em quais filiais este equipamento existe (quantidade e valores de
                locação de cada uma) clicando no ícone de estoque na lista.
              </p>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeDialog}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSaving || !form.categoria_id}>
                {isSaving ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
