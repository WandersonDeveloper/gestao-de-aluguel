import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, RefreshCw, Smartphone } from "lucide-react";
import { toast } from "sonner";

import { api, getApiErrorMessage } from "@/services/api";
import type { MessageTemplate, MessageTemplateKey, WhatsappConnectResult, WhatsappStatus } from "@/types/api";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const templateLabels: Record<MessageTemplateKey, string> = {
  cobranca_fatura: "Mensagem de cobrança",
  contrato_assinatura: "Mensagem de pedido de assinatura",
  aceite_confirmado: "Resposta ao aceitar os termos (opção 1)",
  aceite_recusado: "Resposta ao não aceitar os termos (opção 2)",
  aditivo_confirmacao: "Mensagem de confirmação de aditivo (item adicionado)",
  aditivo_aceite_confirmado: "Resposta ao aceitar o aditivo (opção 1)",
  aditivo_aceite_recusado: "Resposta ao não aceitar o aditivo (opção 2)",
};

const templateVariaveis: Record<MessageTemplateKey, { nome: string; descricao: string }[]> = {
  cobranca_fatura: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "situacao", descricao: '"pendente" ou "em atraso"' },
    { nome: "valor", descricao: "Valor da fatura formatado (ex.: R$ 500,00)" },
    { nome: "vencimento", descricao: "Data de vencimento (dd/mm/aaaa)" },
    { nome: "multa_texto", descricao: "Frase sobre a multa aplicada (vazio se não houver atraso)" },
  ],
  contrato_assinatura: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "tipo_contrato", descricao: 'Ex.: "contrato de locação de equipamentos"' },
    { nome: "contrato_id", descricao: "Número do contrato" },
  ],
  aceite_confirmado: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "contrato_id", descricao: "Número do contrato" },
    { nome: "prazo_entrega", descricao: "Data de início do contrato (dd/mm/aaaa)" },
  ],
  aceite_recusado: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "contrato_id", descricao: "Número do contrato" },
  ],
  aditivo_confirmacao: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "contrato_id", descricao: "Número do contrato" },
    { nome: "itens_descricao", descricao: "Equipamento(s) adicionado(s), ex.: \"Andaime x2\"" },
    { nome: "periodo", descricao: "Período do item adicionado (dd/mm/aaaa até dd/mm/aaaa)" },
    { nome: "valor_texto", descricao: "Frase sobre o valor adicional (vazio se não houver cobrança)" },
  ],
  aditivo_aceite_confirmado: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "contrato_id", descricao: "Número do contrato" },
  ],
  aditivo_aceite_recusado: [
    { nome: "cliente_nome", descricao: "Nome do cliente" },
    { nome: "contrato_id", descricao: "Número do contrato" },
  ],
};

const estadoLabels: Record<string, string> = {
  open: "Conectado",
  connecting: "Conectando",
  close: "Desconectado",
};

const estadoVariant: Record<string, "success" | "warning" | "secondary"> = {
  open: "success",
  connecting: "warning",
  close: "secondary",
};

function TemplateCard({ template }: { template: MessageTemplate }) {
  const queryClient = useQueryClient();
  const [conteudo, setConteudo] = useState(template.conteudo);
  const [tab, setTab] = useState<"mensagem" | "variaveis">("mensagem");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const updateMutation = useMutation({
    mutationFn: async () => api.put(`/settings/message-templates/${template.chave}`, { conteudo }),
    onSuccess: () => {
      toast.success("Template salvo com sucesso.");
      queryClient.invalidateQueries({ queryKey: ["settings", "message-templates"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  function inserirVariavel(nome: string) {
    const textarea = textareaRef.current;
    const placeholder = `{${nome}}`;
    if (!textarea) {
      setConteudo((atual) => atual + placeholder);
      return;
    }
    const inicio = textarea.selectionStart ?? conteudo.length;
    const fim = textarea.selectionEnd ?? conteudo.length;
    const novoConteudo = conteudo.slice(0, inicio) + placeholder + conteudo.slice(fim);
    setConteudo(novoConteudo);
    setTab("mensagem");
    requestAnimationFrame(() => {
      textarea.focus();
      const posicao = inicio + placeholder.length;
      textarea.setSelectionRange(posicao, posicao);
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{templateLabels[template.chave]}</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={tab} onValueChange={(value) => setTab(value as "mensagem" | "variaveis")}>
          <TabsList>
            <TabsTrigger value="mensagem">Mensagem</TabsTrigger>
            <TabsTrigger value="variaveis">Variáveis</TabsTrigger>
          </TabsList>

          <TabsContent value="mensagem" className="flex flex-col gap-2">
            <Textarea ref={textareaRef} rows={4} value={conteudo} onChange={(e) => setConteudo(e.target.value)} />
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={() => updateMutation.mutate()}
                disabled={updateMutation.isPending || conteudo === template.conteudo}
              >
                {updateMutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="variaveis">
            <p className="mb-2 text-xs text-slate-500">Clique em uma variável para inserir na mensagem.</p>
            <div className="flex flex-col divide-y divide-slate-100 rounded-md border border-slate-200">
              {templateVariaveis[template.chave].map((variavel) => (
                <button
                  key={variavel.nome}
                  type="button"
                  onClick={() => inserirVariavel(variavel.nome)}
                  className="flex items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <code className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-700">
                    {`{${variavel.nome}}`}
                  </code>
                  <span className="text-xs text-slate-500">{variavel.descricao}</span>
                </button>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

const QR_REFRESH_MS = 25000;

function WhatsappConnectionCard() {
  const queryClient = useQueryClient();
  const [pairing, setPairing] = useState(false);

  const { data: status } = useQuery({
    queryKey: ["settings", "whatsapp", "status"],
    queryFn: async () => (await api.get<WhatsappStatus>("/settings/whatsapp/status")).data,
    refetchInterval: (query) => (query.state.data?.estado === "open" ? false : 5000),
  });

  const estado = status?.estado ?? null;
  const conectado = estado === "open";

  const qrQuery = useQuery({
    queryKey: ["settings", "whatsapp", "qrcode"],
    queryFn: async () => (await api.post<WhatsappConnectResult>("/settings/whatsapp/connect")).data,
    enabled: pairing && !conectado,
    refetchInterval: pairing && !conectado ? QR_REFRESH_MS : false,
    refetchIntervalInBackground: true,
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => api.post("/settings/whatsapp/disconnect"),
    onSuccess: () => {
      toast.success("WhatsApp desconectado.");
      setPairing(false);
      queryClient.invalidateQueries({ queryKey: ["settings", "whatsapp", "status"] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error)),
  });

  useEffect(() => {
    if (conectado) setPairing(false);
  }, [conectado]);

  useEffect(() => {
    if (qrQuery.error) toast.error(getApiErrorMessage(qrQuery.error));
  }, [qrQuery.error]);

  const qrcode = qrQuery.data?.qrcode_base64;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Conexão WhatsApp</CardTitle>
        <Badge variant={estado ? estadoVariant[estado] : "secondary"} className="gap-1">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              conectado ? "bg-emerald-600" : estado === "connecting" ? "bg-amber-600" : "bg-slate-400"
            }`}
          />
          {estado ? estadoLabels[estado] : "Não configurado"}
        </Badge>
      </CardHeader>
      <CardContent>
        {conectado ? (
          <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
            <div className="flex items-center gap-2 text-emerald-800">
              <CheckCircle2 className="h-5 w-5" />
              <p className="text-sm font-medium">WhatsApp conectado e pronto para enviar mensagens.</p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => disconnectMutation.mutate()}
              disabled={disconnectMutation.isPending}
            >
              {disconnectMutation.isPending ? "Desconectando..." : "Desconectar"}
            </Button>
          </div>
        ) : !pairing ? (
          <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-200 py-10 text-center">
            <Smartphone className="h-8 w-8 text-slate-400" />
            <p className="max-w-sm text-sm text-slate-500">
              Conecte um número de WhatsApp para poder enviar cobranças e contratos direto do sistema.
            </p>
            <Button onClick={() => setPairing(true)}>Conectar WhatsApp</Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 py-2 sm:flex-row sm:items-start sm:justify-center">
            <div className="flex h-64 w-64 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
              {qrQuery.isFetching && !qrcode ? (
                <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
              ) : qrcode ? (
                <img src={qrcode} alt="QR code para parear o WhatsApp" className="h-full w-full object-contain" />
              ) : (
                <p className="px-4 text-center text-sm text-slate-400">Não foi possível gerar o QR code.</p>
              )}
            </div>
            <div className="flex max-w-xs flex-col gap-3">
              <ol className="list-inside list-decimal space-y-1.5 text-sm text-slate-600">
                <li>Abra o WhatsApp no celular</li>
                <li>Toque em Configurações (ou os três pontinhos) &gt; Aparelhos conectados</li>
                <li>Toque em "Conectar um aparelho" e escaneie o código ao lado</li>
              </ol>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => qrQuery.refetch()} disabled={qrQuery.isFetching}>
                  <RefreshCw className={`h-3.5 w-3.5 ${qrQuery.isFetching ? "animate-spin" : ""}`} />
                  Gerar novo código
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setPairing(false)}>
                  Cancelar
                </Button>
              </div>
              <p className="text-xs text-slate-400">
                O código se renova sozinho a cada {Math.round(QR_REFRESH_MS / 1000)}s. A tela atualiza
                automaticamente assim que o celular conectar.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function SettingsPage() {
  const { data: templates } = useQuery({
    queryKey: ["settings", "message-templates"],
    queryFn: async () => (await api.get<MessageTemplate[]>("/settings/message-templates")).data,
  });

  return (
    <div>
      <PageHeader title="Configurações" description="Integração com WhatsApp e templates de mensagem" />

      <div className="grid grid-cols-1 gap-6">
        <WhatsappConnectionCard />

        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
            Templates de mensagem
          </h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {templates?.map((template) => (
              <TemplateCard key={template.chave} template={template} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
