const util = require('util');
const exec = util.promisify(require('child_process').exec);
const readFile = require('fs').readFileSync

async function checkSync(targets) {
    const endpoints = readFile(targets, 'utf8')
    const data = JSON.parse(endpoints)
    for (const endpoint of data.endpoints) {
    try {
        const { stdout, stderr } = await exec('curl --connect-timeout 2 -s ' + endpoint + "/eth/v1/node/syncing");
        if (stderr) {
            console.log('Error: ' + endpoint)
        }
        if (stdout) {
            let stdData = JSON.parse(stdout)
            console.log('Success: ' + endpoint + `    SYNCING: ${stdData.data.is_syncing}    DISTANCE: ${stdData.data.sync_distance}`)
        }
    } catch (error) {
        console.log('Error: ' + endpoint)
    }
    }
}

async function joinEndpoints(targets, wanted, http = false) {
    const endpoints = readFile(targets, 'utf8')
    const data = JSON.parse(endpoints)
    let joined = []
    wanted = wanted.split(' ')
    wanted.forEach(wanted => {
        let found = data.endpoints.find(e => e.split(':')[0].split('.').splice(-1)[0] == wanted)
        if(found){
            joined.push(http ? 'http://' + found : found)
        }else{
            console.log('Endpoint not found: ' + wanted)
        }
    });
    console.log(joined.join(','))
}
checkSync('endpoints-example.json')
joinEndpoints('endpoints-example.json','1 2 3 4', true)