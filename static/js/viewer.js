/**
 * This file demonstrates the process of starting WebRTC streaming using a KVS Signaling Channel.
 */
const viewer = {};

async function startViewer(remoteView, formValues) {
    try {
        console.log('[VIEWER] Channel name is:', formValues.channelName);
        console.log(KVSWebRTC.Role);
        viewerButtonPressed = new Date();

        viewer.remoteView = remoteView;
        console.log(formValues.region);
        console.log(formValues.accessKeyId);
        console.log(formValues.secretAccessKey);

        // Create KVS client
        const kinesisVideoClient = new AWS.KinesisVideo({
            region: formValues.region,
            accessKeyId: formValues.accessKeyId,
            secretAccessKey: formValues.secretAccessKey,
            correctClockSkew: true,
        });
        console.log(kinesisVideoClient);

        const channelARN = "arn:aws:kinesisvideo:ap-southeast-1:822124228671:channel/FishTankWebrtc/1714814825548";
        console.log('[VIEWER] Channel ARN:', channelARN);

        // Get signaling channel endpoints

        const getSignalingChannelEndpointResponse = await kinesisVideoClient
            .getSignalingChannelEndpoint({
                ChannelARN: channelARN,
                SingleMasterChannelEndpointConfiguration: {
                    Protocols: ['WSS', 'HTTPS'],
                    Role: KVSWebRTC.Role.VIEWER,
                },
            })
            .promise();

        const endpointsByProtocol = getSignalingChannelEndpointResponse.ResourceEndpointList.reduce((endpoints, endpoint) => {
            endpoints[endpoint.Protocol] = endpoint.ResourceEndpoint;
            return endpoints;
        }, {});
        console.log('[VIEWER] Endpoints:', endpointsByProtocol);

        const kinesisVideoSignalingChannelsClient = new AWS.KinesisVideoSignalingChannels({
            region: formValues.region,
            accessKeyId: formValues.accessKeyId,
            secretAccessKey: formValues.secretAccessKey,
            endpoint: endpointsByProtocol.HTTPS,
            correctClockSkew: true,
        });

        // Get ICE server configuration
        const getIceServerConfigResponse = await kinesisVideoSignalingChannelsClient
            .getIceServerConfig({
                ChannelARN: channelARN,
            })
            .promise();

        const iceServers = [];
        // Don't add stun if user selects TURN only or NAT traversal disabled
        if (!formValues.natTraversalDisabled && !formValues.forceTURN) {
            iceServers.push({ urls: `stun:stun.kinesisvideo.${formValues.region}.amazonaws.com:443` });
        }

        // Don't add turn if user selects STUN only or NAT traversal disabled
        if (!formValues.natTraversalDisabled && !formValues.forceSTUN) {
            getIceServerConfigResponse.IceServerList.forEach(iceServer =>
                iceServers.push({
                    urls: iceServer.Uris,
                    username: iceServer.Username,
                    credential: iceServer.Password,
                }),
            );
        }
        console.log('[VIEWER] ICE servers:', iceServers);

        // Create Signaling Client
        viewer.signalingClient = new KVSWebRTC.SignalingClient({
            channelARN,
            channelEndpoint: endpointsByProtocol.WSS,
            clientId: formValues.clientId,
            role: KVSWebRTC.Role.VIEWER,
            region: formValues.region,
            credentials: {
                accessKeyId: formValues.accessKeyId,
                secretAccessKey: formValues.secretAccessKey,
                sessionToken: formValues.sessionToken,
            },
            systemClockOffset: kinesisVideoClient.config.systemClockOffset,
        });

        const resolution = formValues.widescreen
            ? {
                  width: { ideal: 1280 },
                  height: { ideal: 720 },
              }
            : { width: { ideal: 640 }, height: { ideal: 480 } };
        const constraints = {
            video: false,
            audio: false,
        };
        const configuration = {
            iceServers,
            iceTransportPolicy: formValues.forceTURN ? 'relay' : 'all',
        };
        viewer.peerConnection = new RTCPeerConnection(configuration);



        viewer.signalingClient.on('open', async () => {


            console.log('[VIEWER] Connected to signaling service');

            // Create an SDP offer to send to the master
            console.log('[VIEWER] Creating SDP offer');
            await viewer.peerConnection.setLocalDescription(
                await viewer.peerConnection.createOffer({
                    offerToReceiveAudio: true,
                    offerToReceiveVideo: true,
                }),
            );

            // When trickle ICE is enabled, send the offer now and then send ICE candidates as they are generated. Otherwise wait on the ICE candidates
            console.log('[VIEWER] Sending SDP offer');
            console.debug('SDP offer:', viewer.peerConnection.localDescription);
            viewer.signalingClient.sendSdpOffer(viewer.peerConnection.localDescription);

            console.log('[VIEWER] Generating ICE candidates');
        });

        viewer.signalingClient.on('sdpAnswer', async answer => {
            // Add the SDP answer to the peer connection
            console.log('[VIEWER] Received SDP answer');
            console.debug('SDP answer:', answer);
            await viewer.peerConnection.setRemoteDescription(answer);
        });

        viewer.signalingClient.on('iceCandidate', candidate => {
            // Add the ICE candidate received from the MASTER to the peer connection
            console.log('[VIEWER] Received ICE candidate');
            console.debug('ICE candidate', candidate);
            viewer.peerConnection.addIceCandidate(candidate);
        });

        viewer.signalingClient.on('close', () => {
            console.log('[VIEWER] Disconnected from signaling channel');
        });

        viewer.signalingClient.on('error', error => {
            console.error('[VIEWER] Signaling client error:', error);
        });

        // Send any ICE candidates to the other peer
        viewer.peerConnection.addEventListener('icecandidate', ({ candidate }) => {
            if (candidate) {
                console.log('[VIEWER] Generated ICE candidate');
                console.debug('ICE candidate:', candidate);

                // When trickle ICE is enabled, send the ICE candidates as they are generated.
                viewer.signalingClient.sendIceCandidate(candidate);

            } else {
                console.log('[VIEWER] All ICE candidates have been generated');

                // When trickle ICE is disabled, send the offer now that all the ICE candidates have ben generated.
                console.log('[VIEWER] Sending SDP offer');
                console.debug('SDP offer:', viewer.peerConnection.localDescription);
                viewer.signalingClient.sendSdpOffer(viewer.peerConnection.localDescription);

            }
        });


        // As remote tracks are received, add them to the remote view
        viewer.peerConnection.addEventListener('track', event => {
            console.log('[VIEWER] Received remote track');
            if (remoteView.srcObject) {
                return;
            }
            $('#viewer').removeClass('d-none');
            viewer.remoteStream = event.streams[0];
            remoteView.srcObject = viewer.remoteStream;

        });

        console.log('[VIEWER] Starting viewer connection');
        viewer.signalingClient.open();
    }
    catch (e) {
        console.error('[VIEWER] Encountered error starting:', e);
    }
}

function stopViewer() {
    try {
        console.log('[VIEWER] Stopping viewer connection');

        if (viewer.signalingClient) {
            viewer.signalingClient.close();
            viewer.signalingClient = null;
        }

        if (viewer.peerConnection) {
            viewer.peerConnection.close();
            viewer.peerConnection = null;
        }

        if (viewer.remoteStream) {
            viewer.remoteStream.getTracks().forEach(track => track.stop());
            viewer.remoteStream = null;
        }

        if (viewer.remoteView) {
            viewer.remoteView.srcObject = null;
        }

    } catch (e) {
        console.error('[VIEWER] Encountered error stopping', e);
    }
}


