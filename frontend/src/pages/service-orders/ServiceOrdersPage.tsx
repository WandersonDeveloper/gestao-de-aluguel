import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { Equipment, ServiceOrder, ServiceOrderPriority, ServiceOrderType } from "@/types/api";
import { serviceOrderStatusLabels, serviceOrderStatusVariant } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type FormState = {
  equipamento_id: string;
  tipo: ServiceOrderType;
  descricao: string;
  prioridade: ServiceOrderPriority;
};

const emptyForm: FormState = { equipamento_id: "", tipo: "preventiva", descricao: "", prioridade: "media" };

export function ServiceOrdersPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [closingOrder, setClosingOrder] = useState<{ id: number; action: "complete" | "cancel" } | null>(null);
  const [closeObservacoes, setCloseObservacoes] = useState("");

  const { data: orders, isLoading } = useQuery({
    queryKey: ["service-orders", statusFilter],
    queryFn: async () =>
      (
        await api.get<ServiceOrder[]>("/service-orders", {
          params: statusFilter !== "todos" ? { status: statusFilter } : {},
        })
      ).data,
  });

  const { data: equipmentList } = useQuery({
    queryKey: ["equipment", "all"],
    queryFn: async () => (await api.get<Equipment[]>("/equipment", { params: { limit: 500 } })).data,
  });

  const equipmentById = new Map((equipmentList ?? []).map((e) => [e.id, e.nome]));

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["service-orders"] });

  const createMutation = useMutation({
    mutationFn: async (payload: FormState) =>
      api.post("/service-orders", { ...payload, equipamento_id: Number(payload.equipamento_id) }),
    onSuccess: () => {
      toast.success("Ordem de serviço criada com sucesso.");
      invalidate();
      setDialogOpen(false);
      setForm(emptyForm);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const startMutation = useMutation({
    mutationFn: async (id: number) => api.post(`/service-orders/${id}/start`),
    onSuccess: () => {
      toast.success("OS iniciada.");
      invalidate();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const closeMutation = useMutation({
    mutationFn: async () =>
      api.post(`/service-orders/${closingOrder!.id}/${closingOrder!.action}`, {
        observacoes: closeObservacoes || null,
      }),
    onSuccess: () => {
      toast.success(closingOrder?.action === "complete" ? "OS concluída." : "OS cancelada.");
      invalidate();
      setClosingOrder(null);
      setCloseObservacoes("");
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
        title="Ordens de Serviço"
        description="Manutenção preventiva e corretiva dos equipamentos"
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> Nova OS
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {Object.entries(serviceOrderStatusLabels).map(([value, label]) => (
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
              <TableHead>Equipamento</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Descrição</TableHead>
              <TableHead>Prioridade</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-56 text-right">Ações</TableHead>
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
            {!isLoading && orders?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-slate-500">
                  Nenhuma ordem de serviço encontrada.
                </TableCell>
              </TableRow>
            )}
            {orders?.map((order) => (
              <TableRow key={order.id}>
                <TableCell>{equipmentById.get(order.equipamento_id) ?? `#${order.equipamento_id}`}</TableCell>
                <TableCell className="capitalize">{order.tipo}</TableCell>
                <TableCell className="max-w-64 truncate">{order.descricao}</TableCell>
                <TableCell className="capitalize">{order.prioridade}</TableCell>
                <TableCell>
                  <Badge variant={serviceOrderStatusVariant[order.status]}>
                    {serviceOrderStatusLabels[order.status]}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {order.status === "aberta" && (
                    <Button size="sm" variant="outline" onClick={() => startMutation.mutate(order.id)}>
                      Iniciar
                    </Button>
                  )}
                  {(order.status === "aberta" || order.status === "em_andamento") && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        className="ml-2"
                        onClick={() => setClosingOrder({ id: order.id, action: "complete" })}
                      >
                        Concluir
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="ml-2"
                        onClick={() => setClosingOrder({ id: order.id, action: "cancel" })}
                      >
                        Cancelar
                      </Button>
                    </>
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
            <DialogTitle>Nova ordem de serviço</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Equipamento</Label>
              <Select
                value={form.equipamento_id}
                onValueChange={(value) => setForm({ ...form, equipamento_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione um equipamento" />
                </SelectTrigger>
                <SelectContent>
                  {equipmentList?.map((equipment) => (
                    <SelectItem key={equipment.id} value={String(equipment.id)}>
                      {equipment.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Tipo</Label>
                <Select value={form.tipo} onValueChange={(value) => setForm({ ...form, tipo: value as ServiceOrderType })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="preventiva">Preventiva</SelectItem>
                    <SelectItem value="corretiva">Corretiva</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Prioridade</Label>
                <Select
                  value={form.prioridade}
                  onValueChange={(value) => setForm({ ...form, prioridade: value as ServiceOrderPriority })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baixa">Baixa</SelectItem>
                    <SelectItem value="media">Média</SelectItem>
                    <SelectItem value="alta">Alta</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="descricao">Descrição</Label>
              <Textarea
                id="descricao"
                required
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending || !form.equipamento_id}>
                {createMutation.isPending ? "Salvando..." : "Criar OS"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!closingOrder} onOpenChange={(open) => !open && setClosingOrder(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{closingOrder?.action === "complete" ? "Concluir OS" : "Cancelar OS"}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="observacoes">Observações (opcional)</Label>
            <Textarea
              id="observacoes"
              value={closeObservacoes}
              onChange={(e) => setCloseObservacoes(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClosingOrder(null)}>
              Voltar
            </Button>
            <Button onClick={() => closeMutation.mutate()} disabled={closeMutation.isPending}>
              {closeMutation.isPending ? "Salvando..." : "Confirmar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
