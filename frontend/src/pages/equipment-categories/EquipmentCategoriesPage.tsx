import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { EquipmentCategory } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type FormState = { nome: string; descricao: string };
const emptyForm: FormState = { nome: "", descricao: "" };

export function EquipmentCategoriesPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<EquipmentCategory | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: categories, isLoading } = useQuery({
    queryKey: ["equipment-categories"],
    queryFn: async () => (await api.get<EquipmentCategory[]>("/equipment-categories")).data,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) =>
      api.post("/equipment-categories", { nome: payload.nome, descricao: payload.descricao || null }),
    onSuccess: () => {
      toast.success("Categoria cadastrada com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment-categories"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: FormState }) =>
      api.patch(`/equipment-categories/${id}`, { nome: payload.nome, descricao: payload.descricao || null }),
    onSuccess: () => {
      toast.success("Categoria atualizada com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["equipment-categories"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/equipment-categories/${id}`),
    onSuccess: () => {
      toast.success("Categoria removida.");
      queryClient.invalidateQueries({ queryKey: ["equipment-categories"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openCreateDialog() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(category: EquipmentCategory) {
    setEditing(category);
    setForm({ nome: category.nome, descricao: category.descricao ?? "" });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditing(null);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function handleDelete(category: EquipmentCategory) {
    if (window.confirm(`Excluir a categoria "${category.nome}"?`)) {
      deleteMutation.mutate(category.id);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Categorias de equipamento"
        description="Classificação usada para organizar os equipamentos"
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4" /> Nova categoria
          </Button>
        }
      />

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Descrição</TableHead>
              <TableHead className="w-24 text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={3} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && categories?.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="py-6 text-center text-slate-500">
                  Nenhuma categoria cadastrada.
                </TableCell>
              </TableRow>
            )}
            {categories?.map((category) => (
              <TableRow key={category.id}>
                <TableCell className="font-medium text-slate-900">{category.nome}</TableCell>
                <TableCell>{category.descricao ?? "—"}</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => openEditDialog(category)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(category)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Editar categoria" : "Nova categoria"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nome">Nome</Label>
              <Input
                id="nome"
                required
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="descricao">Descrição</Label>
              <Textarea
                id="descricao"
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeDialog}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
