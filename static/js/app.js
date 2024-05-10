let ROLE = null; // Possible values: 'master', 'viewer', null
$('#viewer').addClass('d-none');

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
    const form = $('#form');
    ROLE = 'viewer';
    const remoteView = $('#viewer .remote-view')[0];
    const formValues = getFormValues();
    startViewer( remoteView, formValues);
});

function onStop() {
    if (!ROLE) {
        return;
    }
    if (ROLE === 'viewer') {
        stopViewer();
        $('#viewer').addClass('d-none');
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
