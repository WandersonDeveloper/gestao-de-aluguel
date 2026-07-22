import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ChevronDown, FileCheck2, FileDown, MessageCircle, Plus } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { Client, ContractAmendment, ContractWithItems, Equipment, Filial, Invoice } from "@/types/api";
import {
  contractSignatureStatusLabels,
  contractSignatureStatusVariant,
  contractStatusLabels,
  contractStatusVariant,
  contractTypeLabels,
  formatCurrency,
  formatDate,
  invoiceStatusLabels,
  invoiceStatusVariant,
} from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

const amendmentTypeLabels: Record<string, string> = {
  extensao: "Extensão",
  baixa_total: "Baixa total",
  baixa_parcial: "Baixa parcial",
  cancelamento: "Cancelamento",
  adicao_item: "Adição de item",
};

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const contractId = Number(id);
  const queryClient = useQueryClient();

  const [extendDialogOpen, setExtendDialogOpen] = useState(false);
  const [novaDataFim, setNovaDataFim] = useState("");
  const [extendMotivo, setExtendMotivo] = useState("");

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelMotivo, setCancelMotivo] = useState("");

  const invalidateContract = () => {
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "amendments"] });
    queryClient.invalidateQueries({ queryKey: ["contracts", contractId, "invoices"] });
  };

  const { data: contract } = useQuery({
    queryKey: ["contracts", contractId],
    queryFn: async () => (await api.get<ContractWithItems>(`/contracts/${contractId}`)).data,
    enabled: !!contractId,
    // Enquanto aguarda a resposta do cliente pelo WhatsApp, atualiza sozinho
    // — o webhook confirma em segundo plano, sem nenhuma ação na interface.
    refetchInterval: (query) => (query.state.data?.assinatura_status === "aguardando_confirmacao" ? 5000 : false),
  });

  const { data: amendments } = useQuery({
    queryKey: ["contracts", contractId, "amendments"],
    queryFn: async () => (await api.get<ContractAmendment[]>(`/contracts/${contractId}/amendments`)).data,
    enabled: !!contractId,
  });

  const { data: invoices } = useQuery({
    queryKey: ["contracts", contractId, "invoices"],
    queryFn: async () => (await api.get<Invoice[]>("/invoices", { params: { contrato_id: contractId } })).data,
    enabled: !!contractId,
  });

  const { data: clients } = useQuery({
    queryKey: ["clients", "all"],
    queryFn: async () => (await api.get<Client[]>("/clients", { params: { limit: 500 } })).data,
  });

  const { data: equipmentList } = useQuery({
    queryKey: ["equipment", "all"],
    queryFn: async () => (await api.get<Equipment[]>("/equipment", { params: { limit: 500 } })).data,
  });

  const { data: filiais } = useQuery({
    queryKey: ["filiais"],
    queryFn: async () => (await api.get<Filial[]>("/filiais", { params: { limit: 500 } })).data,
  });

  const activateMutation = useMutation({
    mutationFn: async () => api.post(`/contracts/${contractId}/activate`),
    onSuccess: () => {
      toast.success("Contrato ativado.");
      invalidateContract();
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const extendMutation = useMutation({
    mutationFn: async () =>
      api.post(`/contracts/${contractId}/extend`, { nova_data_fim: novaDataFim, motivo: extendMotivo || null }),
    onSuccess: () => {
      toast.success("Contrato estendido com sucesso.");
      invalidateContract();
      setExtendDialogOpen(false);
      setNovaDataFim("");
      setExtendMotivo("");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const cancelMutation = useMutation({
    mutationFn: async () => api.post(`/contracts/${contractId}/cancel`, { motivo: cancelMotivo || null }),
    onSuccess: () => {
      toast.success("Contrato cancelado.");
      invalidateContract();
      setCancelDialogOpen(false);
      setCancelMotivo("");
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const downloadDocumentMutation = useMutation({
    mutationFn: async () => {
      const response = await api.get(`/contracts/${contractId}/documento`, { responseType: "blob" });
      return response.data as Blob;
    },
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `contrato_${contractId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const sendWhatsappMutation = useMutation({
    mutationFn: async () => api.post(`/contracts/${contractId}/send-whatsapp`),
    onSuccess: () => {
      toast.success("Contrato enviado para assinatura via WhatsApp.");
      queryClient.invalidateQueries({ queryKey: ["contracts", contractId] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const downloadComprovanteMutation = useMutation({
    mutationFn: async () => {
      const response = await api.get(`/contracts/${contractId}/comprovante-assinatura`, { responseType: "blob" });
      return response.data as Blob;
    },
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `comprovante_aceite_contrato_${contractId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  const downloadComprovanteAditivoMutation = useMutation({
    mutationFn: async (amendmentId: number) => {
      const response = await api.get(`/contracts/${contractId}/amendments/${amendmentId}/comprovante-assinatura`, {
        responseType: "blob",
      });
      return { blob: response.data as Blob, amendmentId };
    },
    onSuccess: ({ blob, amendmentId }) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `comprovante_aceite_aditivo_${amendmentId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  if (!contract) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  const clientName = clients?.find((c) => c.id === contract.cliente_id)?.nome ?? `Cliente #${contract.cliente_id}`;
  const equipmentById = new Map((equipmentList ?? []).map((e) => [e.id, e]));
  const filiaisById = new Map((filiais ?? []).map((f) => [f.id, f.nome]));
  const canOperate = contract.status === "ativo" || contract.status === "vencido";
  const isHourly = contract.periodicidade_cobranca === "hora";

  return (
    <div>
      <Link to="/contratos" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Voltar para contratos
      </Link>

      <PageHeader
        title={`Contrato #${contract.id} — ${clientName}`}
        description={`${formatDate(contract.data_inicio)} até ${contract.data_fim ? formatDate(contract.data_fim) : "em aberto"}`}
        actions={
          <div className="flex items-center gap-2">
            {contract.status === "rascunho" && (
              <Button onClick={() => activateMutation.mutate()} disabled={activateMutation.isPending}>
                {activateMutation.isPending ? "Ativando..." : "Ativar contrato"}
              </Button>
            )}
            {canOperate && (
              <>
                {contract.data_fim && (
                  <Button variant="outline" onClick={() => setExtendDialogOpen(true)}>
                    Estender
                  </Button>
                )}
                <Button variant="outline" asChild>
                  <Link to={`/contratos/${contractId}/dar-baixa`}>Dar baixa</Link>
                </Button>
              </>
            )}
            {contract.status === "ativo" && (
              <Button variant="outline" asChild title="Adicionar item (aditivo)">
                <Link to={`/contratos/${contractId}/adicionar-item`}>
                  <Plus className="h-4 w-4" /> Adicionar item
                </Link>
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  Documentos <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => downloadDocumentMutation.mutate()}
                  disabled={downloadDocumentMutation.isPending}
                >
                  <FileDown className="h-4 w-4" />
                  {downloadDocumentMutation.isPending ? "Gerando..." : "Baixar contrato"}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => sendWhatsappMutation.mutate()}
                  disabled={sendWhatsappMutation.isPending}
                >
                  <MessageCircle className="h-4 w-4" />
                  {sendWhatsappMutation.isPending ? "Enviando..." : "Enviar p/ assinatura via WhatsApp"}
                </DropdownMenuItem>
                {contract.assinatura_status === "confirmado" && (
                  <DropdownMenuItem
                    onClick={() => downloadComprovanteMutation.mutate()}
                    disabled={downloadComprovanteMutation.isPending}
                  >
                    <FileCheck2 className="h-4 w-4" />
                    {downloadComprovanteMutation.isPending ? "Gerando..." : "Baixar comprovante"}
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            {(contract.status === "rascunho" || canOperate) && (
              <Button variant="destructive" onClick={() => setCancelDialogOpen(true)}>
                Cancelar
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-6 flex items-center gap-2">
        <Badge variant="outline">{contractTypeLabels[contract.tipo]}</Badge>
        <Badge variant={contractStatusVariant[contract.status]}>{contractStatusLabels[contract.status]}</Badge>
        {contract.assinatura_status !== "nao_enviado" && (
          <Badge variant={contractSignatureStatusVariant[contract.assinatura_status]}>
            {contractSignatureStatusLabels[contract.assinatura_status]}
          </Badge>
        )}
      </div>

      {contract.assinatura_status === "confirmado" && (
        <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <p className="font-medium">
            Aceite confirmado {contract.assinatura_confirmada_em ? `em ${formatDate(contract.assinatura_confirmada_em)}` : ""}
          </p>
          {contract.assinatura_resposta_texto && (
            <p className="mt-1 text-emerald-700">Resposta do cliente: "{contract.assinatura_resposta_texto}"</p>
          )}
        </div>
      )}

      {contract.assinatura_status === "aguardando_confirmacao" && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Contrato enviado, aguardando o cliente responder "1" (aceito) ou "2" (não aceito) pelo WhatsApp.
        </div>
      )}

      {contract.assinatura_status === "recusado" && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-medium">
            Cliente não aceitou os termos
            {contract.assinatura_confirmada_em ? ` (respondido em ${formatDate(contract.assinatura_confirmada_em)})` : ""}
          </p>
          {contract.assinatura_resposta_texto && (
            <p className="mt-1 text-red-700">Resposta do cliente: "{contract.assinatura_resposta_texto}"</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Itens do contrato</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Equipamento</TableHead>
                  <TableHead>Filial</TableHead>
                  <TableHead>Qtd.</TableHead>
                  <TableHead>Período</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>{isHourly ? "Horas" : "Valor"}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contract.itens.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{equipmentById.get(item.equipamento_id)?.nome ?? `#${item.equipamento_id}`}</TableCell>
                    <TableCell>{filiaisById.get(item.filial_id) ?? `#${item.filial_id}`}</TableCell>
                    <TableCell>{item.quantidade}</TableCell>
                    <TableCell>
                      {formatDate(item.data_inicio_item)} –{" "}
                      {item.data_fim_item ? formatDate(item.data_fim_item) : "em aberto"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={item.status === "ativo" ? "success" : "secondary"}>
                        {item.status === "ativo" ? "Ativo" : "Devolvido"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {isHourly ? (item.horas_trabalhadas ?? "—") : formatCurrency(item.valor_item)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Faturas</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Vencimento</TableHead>
                  <TableHead>Valor</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-slate-500">
                      Nenhuma fatura gerada.
                    </TableCell>
                  </TableRow>
                )}
                {invoices?.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell>
                      <Link to={`/faturas/${invoice.id}`} className="hover:underline">
                        {formatDate(invoice.data_vencimento)}
                      </Link>
                    </TableCell>
                    <TableCell>{formatCurrency(invoice.valor)}</TableCell>
                    <TableCell>
                      <Badge variant={invoiceStatusVariant[invoice.status]}>{invoiceStatusLabels[invoice.status]}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Histórico de aditivos</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Item solicitado</TableHead>
                  <TableHead>Data anterior</TableHead>
                  <TableHead>Data nova</TableHead>
                  <TableHead>Motivo</TableHead>
                  <TableHead>Registrado em</TableHead>
                  <TableHead>Confirmação do cliente</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {amendments?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-slate-500">
                      Nenhum aditivo registrado.
                    </TableCell>
                  </TableRow>
                )}
                {amendments?.map((amendment) => (
                  <TableRow key={amendment.id}>
                    <TableCell>{amendmentTypeLabels[amendment.tipo] ?? amendment.tipo}</TableCell>
                    <TableCell>
                      {amendment.tipo === "adicao_item" && amendment.itens.length > 0
                        ? amendment.itens
                            .map(
                              (item) =>
                                `${equipmentById.get(item.equipamento_id)?.nome ?? `#${item.equipamento_id}`} x${item.quantidade}`,
                            )
                            .join(", ")
                        : "—"}
                    </TableCell>
                    <TableCell>{formatDate(amendment.data_anterior)}</TableCell>
                    <TableCell>{formatDate(amendment.data_nova)}</TableCell>
                    <TableCell>{amendment.motivo ?? "—"}</TableCell>
                    <TableCell>{new Date(amendment.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell>
                      {amendment.tipo === "adicao_item" && amendment.assinatura_status !== "nao_enviado" ? (
                        <div className="flex items-center gap-2">
                          <Badge variant={contractSignatureStatusVariant[amendment.assinatura_status]}>
                            {contractSignatureStatusLabels[amendment.assinatura_status]}
                          </Badge>
                          {amendment.assinatura_status === "confirmado" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => downloadComprovanteAditivoMutation.mutate(amendment.id)}
                              disabled={downloadComprovanteAditivoMutation.isPending}
                            >
                              <FileCheck2 className="h-4 w-4" /> Comprovante
                            </Button>
                          )}
                        </div>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Dialog open={extendDialogOpen} onOpenChange={setExtendDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Estender contrato</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nova_data_fim">Nova data final</Label>
              <Input
                id="nova_data_fim"
                type="date"
                value={novaDataFim}
                onChange={(e) => setNovaDataFim(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="extend_motivo">Motivo (opcional)</Label>
              <Textarea id="extend_motivo" value={extendMotivo} onChange={(e) => setExtendMotivo(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExtendDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => extendMutation.mutate()} disabled={extendMutation.isPending || !novaDataFim}>
              {extendMutation.isPending ? "Salvando..." : "Confirmar extensão"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar contrato</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cancel_motivo">Motivo (opcional)</Label>
            <Textarea id="cancel_motivo" value={cancelMotivo} onChange={(e) => setCancelMotivo(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
              Voltar
            </Button>
            <Button variant="destructive" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
              {cancelMutation.isPending ? "Cancelando..." : "Confirmar cancelamento"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
