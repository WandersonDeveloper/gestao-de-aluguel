import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ClientsPage } from "@/pages/clients/ClientsPage";
import { EquipmentCategoriesPage } from "@/pages/equipment-categories/EquipmentCategoriesPage";
import { FiliaisPage } from "@/pages/filiais/FiliaisPage";
import { EquipmentPage } from "@/pages/equipment/EquipmentPage";
import { EquipmentDetailPage } from "@/pages/equipment/EquipmentDetailPage";
import { EquipmentStockPage } from "@/pages/equipment/EquipmentStockPage";
import { SuppliersPage } from "@/pages/suppliers/SuppliersPage";
import { ContractsPage } from "@/pages/contracts/ContractsPage";
import { ContractDetailPage } from "@/pages/contracts/ContractDetailPage";
import { ContractBaixaPage } from "@/pages/contracts/ContractBaixaPage";
import { ContractAddItemPage } from "@/pages/contracts/ContractAddItemPage";
import { ServiceOrdersPage } from "@/pages/service-orders/ServiceOrdersPage";
import { InvoicesPage } from "@/pages/invoices/InvoicesPage";
import { InvoiceDetailPage } from "@/pages/invoices/InvoiceDetailPage";
import { ReportsPage } from "@/pages/reports/ReportsPage";
import { UsersPage } from "@/pages/users/UsersPage";
import { SettingsPage } from "@/pages/settings/SettingsPage";

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="clientes" element={<ClientsPage />} />
            <Route path="categorias" element={<EquipmentCategoriesPage />} />
            <Route path="filiais" element={<FiliaisPage />} />
            <Route path="equipamentos" element={<EquipmentPage />} />
            <Route path="equipamentos/:id" element={<EquipmentDetailPage />} />
            <Route path="equipamentos/:id/estoque" element={<EquipmentStockPage />} />
            <Route path="fornecedores" element={<SuppliersPage />} />
            <Route path="contratos" element={<ContractsPage />} />
            <Route path="contratos/:id" element={<ContractDetailPage />} />
            <Route path="contratos/:id/dar-baixa" element={<ContractBaixaPage />} />
            <Route path="contratos/:id/adicionar-item" element={<ContractAddItemPage />} />
            <Route path="ordens-servico" element={<ServiceOrdersPage />} />
            <Route path="faturas" element={<InvoicesPage />} />
            <Route path="faturas/:id" element={<InvoiceDetailPage />} />
            <Route path="relatorios" element={<ReportsPage />} />
            <Route path="usuarios" element={<UsersPage />} />
            <Route path="configuracoes" element={<SettingsPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
