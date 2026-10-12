export type OdooServerId = 'uat' | 'docker' | 'custom';

export type OdooServer = {
  id: OdooServerId;
  label: string;
  host: string;
  baseUrl: string;
  defaultDb: string;
  databases: readonly string[];
};

export const ODOO_SERVERS: Record<Exclude<OdooServerId, 'custom'>, OdooServer> = {
  uat: {
    id: 'uat',
    label: 'UAT (vpk.24erp.com)',
    host: 'vpk.24erp.com',
    baseUrl: 'https://vpk.24erp.com',
    defaultDb: 'VPK-S1',
    databases: ['VPK-S1'],
  },
  docker: {
    id: 'docker',
    label: 'Local Docker',
    host: '127.0.0.1:8069',
    baseUrl: 'http://127.0.0.1:8069',
    defaultDb: 'VPK-S1',
    databases: ['VPK-S1'],
  },
};

let current: OdooServer = ODOO_SERVERS.docker;

export const ODOO_CONFIG = {
  get baseUrl() {
    return current.baseUrl;
  },
  apiBase: '/vpk/api/v1/maintenance',
  get defaultDb() {
    return current.defaultDb;
  },
  get databases() {
    return current.databases;
  },
  get host() {
    return current.host;
  },
};

export function applyOdooServer(server: Partial<OdooServer> & { baseUrl: string }) {
  const id = server.id || 'custom';
  current = {
    id,
    label: server.label || current.label,
    host: server.host || server.baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, ''),
    baseUrl: server.baseUrl.replace(/\/$/, ''),
    defaultDb: server.defaultDb || 'VPK-S1',
    databases: server.databases || ['VPK-S1'],
  };
}

export function applyOdooServerId(id: OdooServerId, customUrl?: string) {
  if (id === 'docker') {
    applyOdooServer(ODOO_SERVERS.docker);
    return;
  }
  if (id === 'custom' && customUrl) {
    applyOdooServer({
      id: 'custom',
      label: 'กำหนดเอง',
      baseUrl: customUrl.trim().replace(/\/$/, ''),
      defaultDb: 'VPK-S1',
      databases: ['VPK-S1'],
    });
    return;
  }
  applyOdooServer(ODOO_SERVERS.uat);
}

export function apiUrl(path: string) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${ODOO_CONFIG.baseUrl}${ODOO_CONFIG.apiBase}${normalized}`;
}
