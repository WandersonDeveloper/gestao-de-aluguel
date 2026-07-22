import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { Client, ClientType } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type ClientFormState = {
  nome: string;
  tipo: ClientType;
  documento: string;
  telefone: string;
  email: string;
  endereco: string;
  observacoes: string;
};

const emptyForm: ClientFormState = {
  nome: "",
  tipo: "PF",
  documento: "",
  telefone: "",
  email: "",
  endereco: "",
  observacoes: "",
};

export function ClientsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [form, setForm] = useState<ClientFormState>(emptyForm);

  const { data: clients, isLoading } = useQuery({
    queryKey: ["clients", search],
    queryFn: async () => {
      const response = await api.get<Client[]>("/clients", { params: search ? { nome: search } : {} });
      return response.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (payload: ClientFormState) => api.post("/clients", toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Cliente cadastrado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ClientFormState }) =>
      api.patch(`/clients/${id}`, toApiPayload(payload)),
    onSuccess: () => {
      toast.success("Cliente atualizado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      closeDialog();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/clients/${id}`),
    onSuccess: () => {
      toast.success("Cliente removido.");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function toApiPayload(payload: ClientFormState) {
    return {
      nome: payload.nome,
      tipo: payload.tipo,
      documento: payload.documento,
      telefone: payload.telefone || null,
      email: payload.email || null,
      endereco: payload.endereco || null,
      observacoes: payload.observacoes || null,
    };
  }

  function openCreateDialog() {
    setEditing(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEditDialog(client: Client) {
    setEditing(client);
    setForm({
      nome: client.nome,
      tipo: client.tipo,
      documento: client.documento,
      telefone: client.telefone ?? "",
      email: client.email ?? "",
      endereco: client.endereco ?? "",
      observacoes: client.observacoes ?? "",
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

  function handleDelete(client: Client) {
    if (window.confirm(`Excluir o cliente "${client.nome}"?`)) {
      deleteMutation.mutate(client.id);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Clientes"
        description="Cadastro de clientes pessoa física e jurídica"
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4" /> Novo cliente
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
              <TableHead>Tipo</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Telefone</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="w-24 text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && clients?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-slate-500">
                  Nenhum cliente encontrado.
                </TableCell>
              </TableRow>
            )}
            {clients?.map((client) => (
              <TableRow key={client.id}>
                <TableCell className="font-medium text-slate-900">{client.nome}</TableCell>
                <TableCell>{client.tipo}</TableCell>
                <TableCell>{client.documento}</TableCell>
                <TableCell>{client.telefone ?? "—"}</TableCell>
                <TableCell>{client.email ?? "—"}</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => openEditDialog(client)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(client)}>
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
            <DialogTitle>{editing ? "Editar cliente" : "Novo cliente"}</DialogTitle>
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
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={(value) => setForm({ ...form, tipo: value as ClientType })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PF">Pessoa Física</SelectItem>
                    <SelectItem value="PJ">Pessoa Jurídica</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="documento">Documento</Label>
                <Input
                  id="documento"
                  required
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
              <div className="flex flex-col gap-1.5">
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
