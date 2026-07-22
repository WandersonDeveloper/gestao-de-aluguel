import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { Supplier } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type FormState = {
  nome: string;
  documento: string;
  telefone: string;
  email: string;
  endereco: string;
  observacoes: string;
};

const emptyForm: FormState = { nome: "", documento: "", telefone: "", email: "", endereco: "", observacoes: "" };

export function SuppliersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: suppliers, isLoading } = useQuery({
    queryKey: ["suppliers", search],
    queryFn: async () =>
      (await api.get<Supplier[]>("/suppliers", { params: search ? { nome: search } : {} })).data,
  });

  function toApiPayload(payload: FormState) {
    return {
      nome: payload.nome,
      documento: payload.documento || null,
      telefone: payload.telefone || null,
      email: payload.email || null,
      endereco: payload.endereco || null,
      observacoes: payload.observacoes || null,
    };
  }

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) => api.post("/suppliers", toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Fornecedor cadastrado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: FormState }) =>
      api.patch(`/suppliers/${id}`, toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Fornecedor atualizado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/suppliers/${id}`),
    onSuccess: () => {
      toast.success("Fornecedor removido.");
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function openCreateDialog() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(supplier: Supplier) {
    setEditing(supplier);
    setForm({
      nome: supplier.nome,
      documento: supplier.documento ?? "",
      telefone: supplier.telefone ?? "",
      email: supplier.email ?? "",
      endereco: supplier.endereco ?? "",
      observacoes: supplier.observacoes ?? "",
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

  function handleDelete(supplier: Supplier) {
    if (window.confirm(`Excluir o fornecedor "${supplier.nome}"?`)) {
      deleteMutation.mutate(supplier.id);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Fornecedores"
        description="Cadastro de fornecedores de peças e serviços"
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4" /> Novo fornecedor
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
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Telefone</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="w-24 text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && suppliers?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-6 text-center text-slate-500">
                  Nenhum fornecedor encontrado.
                </TableCell>
              </TableRow>
            )}
            {suppliers?.map((supplier) => (
              <TableRow key={supplier.id}>
                <TableCell className="font-medium text-slate-900">{supplier.nome}</TableCell>
                <TableCell>{supplier.documento ?? "—"}</TableCell>
                <TableCell>{supplier.telefone ?? "—"}</TableCell>
                <TableCell>{supplier.email ?? "—"}</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => openEditDialog(supplier)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(supplier)}>
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
            <DialogTitle>{editing ? "Editar fornecedor" : "Novo fornecedor"}</DialogTitle>
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
                <Label htmlFor="documento">Documento</Label>
                <Input
                  id="documento"
                  value={form.documento}
                  onChange={(e) => setForm({ ...form, documento: e.target.value })}
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
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
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
