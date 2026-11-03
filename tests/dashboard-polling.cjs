const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const archivo = process.argv[2] || require('node:path').join(__dirname, '../static/js/panel-dashboard.js');
const codigo = fs.readFileSync(archivo, 'utf8');
const aviso = { hidden: true, textContent: '' };
let timers = [];
const context = vm.createContext({
  URL, AbortController, TypeError, SyntaxError,
  window: { location: { origin: 'http://localhost' } },
  document: { getElementById: () => aviso },
  setTimeout: (callback, delay) => { const timer = { callback, delay }; timers.push(timer); return timer; },
  clearTimeout: timer => { timers = timers.filter(t => t !== timer); },
});
vm.runInContext(codigo.slice(0, codigo.indexOf('var ctx =')), context);
const respuesta = (opciones = {}) => ({
  url: 'http://localhost/panel/api/stats/', status: 200, ok: true,
  headers: { get: () => 'application/json' }, json: async () => ({ total: 3 }),
  ...opciones,
});
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  context.fetch = async () => respuesta();
  assert.equal((await context.obtenerJSON('/test')).total, 3);
  assert.equal(timers.length, 0);
  for (const [opciones, esperado] of [
    [{status: 401, ok: false}, /sesión/],
    [{redirected: true, url: 'http://localhost/cuentas/login/'}, /sesión/],
    [{status: 403, ok: false}, /permiso/],
    [{status: 500, ok: false}, /500/],
    [{headers: {get: () => 'text/html'}}, /esperados/],
    [{json: async () => { throw new SyntaxError('invalid'); }}, /válida/],
  ]) {
    context.fetch = async () => respuesta(opciones);
    await assert.rejects(context.obtenerJSON('/test'), esperado);
    assert.equal(timers.length, 0);
  }
  context.fetch = async () => { throw new TypeError('network'); };
  await assert.rejects(context.obtenerJSON('/test'), /conexión/);
  context.fetch = (_, {signal}) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(Object.assign(new Error(), {name: 'AbortError'})));
  });
  const pendiente = context.obtenerJSON('/test');
  const rechazo = assert.rejects(pendiente, /tardó/);
  timers[0].callback();
  await rechazo;
  assert.equal(timers.length, 0);
  context.mostrarEstadoDashboard('A', 'Fallo A');
  context.mostrarEstadoDashboard('B', 'Fallo B');
  context.mostrarEstadoDashboard('A', '');
  assert.equal(aviso.textContent, 'B: Fallo B');
  context.mostrarEstadoDashboard('B', '');
  assert.equal(aviso.hidden, true);
  let resolver;
  let llamadas = 0;
  context.iniciarActualizacion('Prueba', () => { llamadas++; return new Promise(r => { resolver = r; }); }, 5000);
  assert.equal(llamadas, 1);
  assert.equal(timers.length, 0, 'No se programa otra consulta mientras la primera sigue pendiente');
  resolver();
  await flush();
  assert.equal(timers.length, 1);
  assert.equal(timers[0].delay, 5000);
  timers = [];
  context.iniciarActualizacion('Prueba', async () => { throw new Error('Fallo simulado'); }, 5000);
  await flush();
  assert.match(aviso.textContent, /Fallo simulado/);
  assert.equal(timers.length, 1, 'Se reintenta también tras un fallo');
  console.log('OK: JSON, errores HTTP/sesión, red, timeout, avisos independientes y consultas sin solapamiento.');
})().catch(error => { console.error(error); process.exitCode = 1; });
