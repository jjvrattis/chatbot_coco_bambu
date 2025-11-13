#!/usr/bin/env node
import { criarPixCheckout } from './checkout.js';

const [,, produtoNome, valorCentavos, clienteNome, clienteTelefone, expiresSeconds, clienteCpf] = process.argv;

criarPixCheckout(
    produtoNome,
    parseInt(valorCentavos),
    clienteNome,
    clienteTelefone,
    'cliente@email.com',
    clienteCpf || '',
    parseInt(expiresSeconds || '3600')
).then(result => {
    console.log(JSON.stringify(result));
    process.exit(0);
}).catch(error => {
    console.error(JSON.stringify({ success: false, error: error.message }));
    process.exit(1);
});
// moved to python/
