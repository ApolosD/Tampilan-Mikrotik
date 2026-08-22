# Development roadmap

## Phase 1-2: foundation and dashboard - current

- [x] Project folder terpisah dari backup `Monitor Data`
- [x] Modular structure
- [x] SQLite schema
- [x] Seed initial data
- [x] Streamlit navigation
- [x] Quota engine dengan actual/display usage
- [x] Basic dashboard, crew, plan, transactions, logs, settings
- [x] Unlimited and Limited mode switching with quota preservation
- [x] Access points, devices, and bandwidth pages
- [x] Quota allocation and add-on flow
- [x] Analytics, forecast, alerts, firewall readiness
- [x] Security role matrix
- [x] CSV, Excel, and PDF report downloads

## Phase 3: MikroTik integration - intentionally last

- [ ] RouterOS connection adapter
- [ ] System resource and uptime
- [ ] Hotspot users and active sessions
- [ ] Interface traffic
- [ ] Firewall/address-list monitoring
- [ ] Access Point discovery contract

## Phase 4: crew management

- [ ] Create/update crew profile
- [ ] User/device mapping
- [ ] Role-based operator actions
- [ ] Online/offline reconciliation

## Phase 5-7: quota and control

- [ ] Equal, custom, shared pool allocation
- [ ] Usage snapshots
- [ ] Auto warning and auto block
- [ ] Block/unblock/disconnect RouterOS action
- [ ] Add-on, transfer, adjustment, refund, reset transactions

## Phase 8-10: intelligence and governance

- [ ] Daily/weekly/monthly analytics
- [ ] Usage forecast and exhaustion warning
- [ ] Admin/operator/viewer authentication
- [x] CSV, Excel, PDF reports
- [ ] Backup, restore, migrations, audit hardening

## Acceptance gates

1. Domain tests pass before RouterOS control is enabled.
2. Actual usage never changes because of display rules.
3. Every quota mutation has a transaction and audit log.
4. Destructive network actions require authorization and explicit confirmation.
5. Live integration is tested against an authorized MikroTik only.
