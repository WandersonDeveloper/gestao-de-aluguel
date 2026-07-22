import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { AppUser, UserRoleValue } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const roleLabels: Record<string, string> = { admin: "Administrador", operador: "Operador", financeiro: "Financeiro" };

type FormState = { nome: string; email: string; senha: string; papel: UserRoleValue };
const emptyForm: FormState = { nome: "", email: "", senha: "", papel: "operador" };

export function UsersPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<AppUser[]>("/users")).data,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) => api.post("/users", payload),
    onSuccess: () => {
      toast.success("Usuário criado com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setDialogOpen(false);
      setForm(emptyForm);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    createMutation.mutate(form);
  }

  return (
    <div>
      <PageHeader
        title="Usuários"
        description="Gestão de acesso ao sistema"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> Novo usuário
          </Button>
        }
      />

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Papel</TableHead>
              <TableHead>Status</TableHead>
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
            {users?.map((appUser) => (
              <TableRow key={appUser.id}>
                <TableCell className="font-medium text-slate-900">{appUser.nome}</TableCell>
                <TableCell>{appUser.email}</TableCell>
                <TableCell>{roleLabels[appUser.papel]}</TableCell>
                <TableCell>
                  <Badge variant={appUser.ativo ? "success" : "secondary"}>
                    {appUser.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo usuário</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nome">Nome</Label>
              <Input id="nome" required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="senha">Senha</Label>
              <Input
                id="senha"
                type="password"
                required
                minLength={8}
                value={form.senha}
                onChange={(e) => setForm({ ...form, senha: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Papel</Label>
              <Select value={form.papel} onValueChange={(value) => setForm({ ...form, papel: value as UserRoleValue })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Administrador</SelectItem>
                  <SelectItem value="operador">Operador</SelectItem>
                  <SelectItem value="financeiro">Financeiro</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
