import { startViewer,stopViewer, streamToServer } from "/static/js/viewer.js"

let ROLE = null; // Possible values: 'master', 'viewer', null
$('#viewer').addClass('d-none');
$('#server').addClass('d-none');

const v = $('#viewer .remote-view')[0];
v.addEventListener( "loadedmetadata", function (e) {
    var width = this.videoWidth,
        height = this.videoHeight;
    console.log("[VIDEO DIMENSIONS] ", width," ", height);
}, false );
const s = $('#server .server-view')[0];
s.addEventListener( "loadedmetadata", function (e) {
    var width = this.videoWidth,
        height = this.videoHeight;
    console.log("[VIDEO DIMENSIONS] ", width," ", height);
}, false );
function getRandomClientId() {
    return Math.random()
        .toString(36)
        .substring(2)
        .toUpperCase();
}

function getFormValues() {
    return {
        region: $('#region').val(),
        channelName: $('#channelName').val(),
        clientId: $('#clientId').val() || getRandomClientId(),
        accessKeyId: $('#accessKeyId').val(),
        endpoint: $('#endpoint').val() || null,
        secretAccessKey: $('#secretAccessKey').val(),
        sessionToken: $('#sessionToken').val() || null
    };
}
$('#stop-stream-button').click(onStop);


$('#stream-button').click(async () => {
    const formValues = getFormValues();
    const a = fetch('/startStreaming', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ param: formValues.channelName }),
                });
    $('#server').removeClass('d-none');
    const form = $('#form');
    ROLE = 'viewer';
    const remoteView = $('#viewer .remote-view')[0];

    startViewer( remoteView, formValues);

//    streamToServer();

});

function onStop() {
    const a = fetch("/stopStreaming");

    if (!ROLE) {
        return;
    }
    if (ROLE === 'viewer') {
        stopViewer();
        $('#viewer').addClass('d-none');
        $('#server').addClass('d-none');

    }
    ROLE = null;
}

// Fetch regions
fetch('https://api.regional-table.region-services.aws.a2z.com/index.jsons')
    .then(res => {
        if (res.ok) {
            return res.json();
        }
        return Promise.reject(`${res.status}: ${res.statusText}`);
    })
    .then(data => {
        data?.prices
            ?.filter(serviceData => serviceData?.attributes['aws:serviceName'] === 'Amazon Kinesis Video Streams')
            .map(kinesisVideoServiceData => kinesisVideoServiceData?.attributes['aws:region'])
            .sort()
            .forEach(region => {
                $('#regionList').append(
                    $('<option>', {
                        value: region,
                        text: region,
                    }),
                );
            });
        $('#region').attr('list', 'regionList');
        console.log('[FETCH-REGIONS] Successfully fetched regions!');
    })
    .catch(err => {
        console.error('[FETCH-REGIONS] Encountered error fetching regions', err);
    });


function randomString() {
    return Date.now().toString();
}
