import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { Filial } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type FormState = {
  nome: string;
  endereco: string;
  telefone: string;
  observacoes: string;
};

const emptyForm: FormState = { nome: "", endereco: "", telefone: "", observacoes: "" };

export function FiliaisPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = user?.papel === "admin";
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Filial | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: filiais, isLoading } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  function toApiPayload(payload: FormState) {
    return {
      nome: payload.nome,
      endereco: payload.endereco || null,
      telefone: payload.telefone || null,
      observacoes: payload.observacoes || null,
    };
  }

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) => api.post("/filiais", toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Filial cadastrada com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["filiais"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: FormState }) =>
      api.patch(`/filiais/${id}`, toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Filial atualizada com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["filiais"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/filiais/${id}`),
    onSuccess: () => {
      toast.success("Filial removida.");
      queryClient.invalidateQueries({ queryKey: ["filiais"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openCreateDialog() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(filial: Filial) {
    setEditing(filial);
    setForm({
      nome: filial.nome,
      endereco: filial.endereco ?? "",
      telefone: filial.telefone ?? "",
      observacoes: filial.observacoes ?? "",
    });
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

  function handleDelete(filial: Filial) {
    if (window.confirm(`Excluir a filial "${filial.nome}"?`)) {
      deleteMutation.mutate(filial.id);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Filiais"
        description="Unidades/depósitos onde os equipamentos ficam alocados"
        actions={
          canManage && (
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4" /> Nova filial
            </Button>
          )
        }
      />

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Endereço</TableHead>
              <TableHead>Telefone</TableHead>
              {canManage && <TableHead className="w-24 text-right">Ações</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={4} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && filiais?.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-6 text-center text-slate-500">
                  Nenhuma filial cadastrada.
                </TableCell>
              </TableRow>
            )}
            {filiais?.map((filial) => (
              <TableRow key={filial.id}>
                <TableCell className="font-medium text-slate-900">{filial.nome}</TableCell>
                <TableCell>{filial.endereco ?? "—"}</TableCell>
                <TableCell>{filial.telefone ?? "—"}</TableCell>
                {canManage && (
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => openEditDialog(filial)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(filial)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Editar filial" : "Nova filial"}</DialogTitle>
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
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="telefone">Telefone</Label>
                <Input
                  id="telefone"
                  value={form.telefone}
                  onChange={(e) => setForm({ ...form, telefone: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label htmlFor="endereco">Endereço</Label>
                <Input
                  id="endereco"
                  value={form.endereco}
                  onChange={(e) => setForm({ ...form, endereco: e.target.value })}
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
