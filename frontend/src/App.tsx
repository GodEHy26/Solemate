import { Route, Routes } from 'react-router-dom';
import { Shell } from './components/layout/Shell';
import { CatalogPage } from './pages/CatalogPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { ConfiguratorPage } from './pages/ConfiguratorPage';
import { HomePage } from './pages/HomePage';
import { OrderPage } from './pages/OrderPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { TermsPage } from './pages/TermsPage';
import { ProfilePage } from './pages/ProfilePage';
import { ScanPage } from './pages/ScanPage';

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/profiles/:id" element={<ProfilePage />} />
        <Route path="/shoes" element={<CatalogPage />} />
        <Route path="/shoes/:slug" element={<ConfiguratorPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/orders/:id" element={<OrderPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="*" element={<div className="container"><h2>Page not found</h2></div>} />
      </Routes>
    </Shell>
  );
}
