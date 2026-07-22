import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, MessageCircle } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { Invoice, InvoiceItem, Payment } from "@/types/api";
import { formatCurrency, formatDate, invoiceStatusLabels, invoiceStatusVariant } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const invoiceId = Number(id);
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManage = user?.papel === "admin" || user?.papel === "financeiro";

  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [valor, setValor] = useState("");
  const [formaPagamento, setFormaPagamento] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["invoices", invoiceId] });
    queryClient.invalidateQueries({ queryKey: ["invoices", invoiceId, "payments"] });
  };

  const { data: invoice } = useQuery({
    queryKey: ["invoices", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
    enabled: !!invoiceId,
  });

  const { data: items } = useQuery({
    queryKey: ["invoices", invoiceId, "items"],
    queryFn: async () => (await api.get<InvoiceItem[]>(`/invoices/${invoiceId}/items`)).data,
    enabled: !!invoiceId,
  });

  const { data: payments } = useQuery({
    queryKey: ["invoices", invoiceId, "payments"],
    queryFn: async () => (await api.get<Payment[]>(`/invoices/${invoiceId}/payments`)).data,
    enabled: !!invoiceId,
  });

  const paymentMutation = useMutation({
    mutationFn: async () =>
      api.post(`/invoices/${invoiceId}/payments`, {
        valor,
        forma_pagamento: formaPagamento || null,
      }),
    onSuccess: () => {
      toast.success("Pagamento registrado com sucesso.");
      invalidate();
      setPaymentDialogOpen(false);
      setValor("");
      setFormaPagamento("");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const cancelMutation = useMutation({
    mutationFn: async () => api.post(`/invoices/${invoiceId}/cancel`),
    onSuccess: () => {
      toast.success("Fatura cancelada.");
      invalidate();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const sendWhatsappMutation = useMutation({
    mutationFn: async () => api.post(`/invoices/${invoiceId}/send-whatsapp`),
    onSuccess: () => toast.success("Cobrança enviada via WhatsApp."),
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  if (!invoice) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const totalPago = (payments ?? []).reduce((sum, p) => sum + Number(p.valor), 0);
  const canPay = canManage && (invoice.status === "pendente" || invoice.status === "atrasada");

  return (
    <div>
      <Link to="/faturas" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Voltar para faturas
      </Link>

      <PageHeader
        title={`Fatura #${invoice.id} — Contrato #${invoice.contrato_id}`}
        description={`Vencimento em ${formatDate(invoice.data_vencimento)}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={invoiceStatusVariant[invoice.status]}>{invoiceStatusLabels[invoice.status]}</Badge>
            {canPay && (
              <Button
                variant="outline"
                onClick={() => sendWhatsappMutation.mutate()}
                disabled={sendWhatsappMutation.isPending}
              >
                <MessageCircle className="h-4 w-4" />
                {sendWhatsappMutation.isPending ? "Enviando..." : "Enviar cobrança via WhatsApp"}
              </Button>
            )}
            {canPay && <Button onClick={() => setPaymentDialogOpen(true)}>Registrar pagamento</Button>}
            {canManage && invoice.status !== "cancelada" && invoice.status !== "paga" && (
              <Button variant="destructive" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
                Cancelar fatura
              </Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Resumo</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Valor</p>
              <p className="text-slate-900">{formatCurrency(invoice.valor)}</p>
            </div>
            <div>
              <p className="text-slate-500">Multa/juros aplicado</p>
              <p className="text-slate-900">{formatCurrency(invoice.multa_juros_aplicado)}</p>
            </div>
            <div>
              <p className="text-slate-500">Total pago</p>
              <p className="text-slate-900">{formatCurrency(totalPago)}</p>
            </div>
            <div>
              <p className="text-slate-500">Nota fiscal</p>
              <p className="text-slate-900">{invoice.numero_nota_fiscal ?? "—"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Itens cobertos</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item do contrato</TableHead>
                  <TableHead>Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items?.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>#{item.contract_item_id}</TableCell>
                    <TableCell>{formatCurrency(item.valor)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pagamentos</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Valor</TableHead>
                  <TableHead>Forma</TableHead>
                  <TableHead>Observações</TableHead>
                  <TableHead>Data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-slate-500">
                      Nenhum pagamento registrado.
                    </TableCell>
                  </TableRow>
                )}
                {payments?.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell>{formatCurrency(payment.valor)}</TableCell>
                    <TableCell>{payment.forma_pagamento ?? "—"}</TableCell>
                    <TableCell>{payment.observacoes ?? "—"}</TableCell>
                    <TableCell>{new Date(payment.created_at).toLocaleString("pt-BR")}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar pagamento</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="valor">Valor</Label>
              <Input id="valor" type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="forma">Forma de pagamento (opcional)</Label>
              <Input
                id="forma"
                placeholder="pix, boleto, dinheiro..."
                value={formaPagamento}
                onChange={(e) => setFormaPagamento(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaymentDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => paymentMutation.mutate()} disabled={paymentMutation.isPending || !valor}>
              {paymentMutation.isPending ? "Salvando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
