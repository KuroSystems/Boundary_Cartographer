/**
 * Outbound-socket guard for the offline harness (S-04 fallback mode).
 * Loaded into every Node process via NODE_OPTIONS="--require <this file>".
 * Blocks outbound net/tls connections to non-loopback hosts (fails loudly).
 */
'use strict';

const net = require('net');
const tls = require('tls');

const ALLOWED_HOSTS = new Set(['127.0.0.1', '::1', 'localhost', '0.0.0.0', '']);

function checkHost(host) {
  if (typeof host === 'string' && host !== '' && !ALLOWED_HOSTS.has(host)) {
    throw new Error(`offline_check: outbound socket to ${host} blocked`);
  }
}

const origNetConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function patchedConnect(...args) {
  const first = args[0];
  if (typeof first === 'object' && first !== null) checkHost(first.host);
  else if (typeof first === 'string') checkHost(first);
  return origNetConnect.apply(this, args);
};

const origTlsConnect = tls.connect;
tls.connect = function patchedTlsConnect(...args) {
  const first = args[0];
  if (typeof first === 'object' && first !== null) checkHost(first.host);
  return origTlsConnect.apply(this, args);
};
