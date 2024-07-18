/**
 * This file demonstrates the process of starting WebRTC streaming using a KVS Signaling Channel.
 */
// Import the functions you need from the SDKs you need
// Import the functions you need from the SDKs you need
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js'
import { doc,getDoc, getFirestore, collection, onSnapshot,setDoc, query, deleteDoc } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js'

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyA6EGqI3xMLvBF0aIfoAgRRgbq6Us7uC24",
    authDomain: "ras-iot-streaming.firebaseapp.com",
    projectId: "ras-iot-streaming",
    storageBucket: "ras-iot-streaming.appspot.com",
    messagingSenderId: "148161552537",
    appId: "1:148161552537:web:36f2710d714ab43749d808"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
const db = getFirestore(app);

const viewer = {};
const receiver = {};
let streamView;

const offerDoc = doc(db,"calls","offers");
deleteDoc(offerDoc);
const answerDoc = doc(db,"calls", "answers");
deleteDoc(answerDoc);

// Listen for real-time updates in the 'yourCollection' collection
const q = query(collection(db, "calls"));
const unsubscribe = onSnapshot(q, (snapshot) => {
  snapshot.docChanges().forEach((change) => {
    if (change.type === "added" && change.doc.id === "answers") {
        console.log("[ANSWER] : Answer received: ", change.doc.data());
        let answer =  change.doc.data();
        receiver.peerConnection.setRemoteDescription(answer);
    }
  });
});

export async function startViewer(remoteView, formValues) {
    try {
        console.log('[VIEWER] Channel name is:', formValues.channelName);
        console.log(KVSWebRTC.Role);
        let viewerButtonPressed = new Date();
        streamView = remoteView;

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
                    Protocols: ['WSS'],
                    Role: KVSWebRTC.Role.VIEWER,
                },
            })
            .promise();

        const endpointsByProtocol = getSignalingChannelEndpointResponse.ResourceEndpointList.reduce((endpoints, endpoint) => {
            endpoints[endpoint.Protocol] = endpoint.ResourceEndpoint;
            return endpoints;
        }, {});
        console.log('[VIEWER] Endpoints:', endpointsByProtocol);

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

//        const resolution = formValues.widescreen
//            ? {
//                  width: { ideal: 1280 },
//                  height: { ideal: 720 },
//              }
//            : { width: { ideal: 640 }, height: { ideal: 480 } };
//        const constraints = {
//            video: false,
//            audio: false,
//        };

        viewer.peerConnection = new RTCPeerConnection();


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
            $('#server').removeClass('d-none');
            $('#viewer').removeClass('d-none');
            viewer.remoteStream = event.streams[0];
            remoteView.srcObject = viewer.remoteStream;
            receiver.stream = event.streams[0];
//            streamToServer();
        });

        console.log('[VIEWER] Starting viewer connection');
        viewer.signalingClient.open();
    }
    catch (e) {
        console.error('[VIEWER] Encountered error starting:', e);
    }
}

// Get stats periodically (example every 5 seconds)
//setInterval(() => {
//    if (viewer.peerConnection){
//        viewer.peerConnection.getStats()
//            .then(stats => {
//                stats.forEach(report => {
//                    console.log(`Report: ${report.type}`);
//                    console.log(report);
//                });
//            })
//            .catch(err => {
//                console.error(err);
//            });
//    }
//}, 2000);

export async function streamToServer(){
    try{
        const constraints = {
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 30 },
          },
          audio: false
        };
        console.log("[Initializing]");
        // STUN server configuration
        var config = {
            iceServers : [{ urls: ['stun:stun.l.google.com:19302'] }]
        };

        receiver.peerConnection = new RTCPeerConnection(config);
        let pc = receiver.peerConnection;
         // register some listeners to help debugging
        pc.addEventListener('icegatheringstatechange', () => {
            console.log("[Ice Gathering State]",pc.iceGatheringState);
        }, false);
        pc.addEventListener('iceconnectionstatechange', () => {
            console.log("[Ice Connection State]",pc.iceGatheringState);
        }, false);

        // connect audio / video
        pc.addEventListener('track', (evt) => {
            if (evt.track.kind == 'video')
                console.log("[VIDEO RECEIVED]");
                receiver.remoteView = $('#server .server-view')[0]
                receiver.remoteStream = evt.streams[0];
                receiver.remoteView.srcObject =receiver.remoteStream;
        });
        // Add tracks to the peer connection
//        let localStream = await navigator.mediaDevices.getUserMedia({ video: true });
//        let localStream = $('#viewer .remote-view')[0].srcObject? $('#viewer .remote-view')[0].srcObject : null;
//       let localStream = $('#webcams .webcam-view')[0].srcObject? $('#webcams .webcam-view')[0].srcObject : null;

        // Add tracks to the peer connection
//        receiver.peerConnection.addTrack(receiver.track)
        receiver.stream.getTracks().forEach(track =>{
            var sender = receiver.peerConnection.addTrack(track, receiver.stream);
            var params = sender.getParameters();
//            params.encodings[0].maxFramerate = 5.0;
//            params.encodings[0].priority = "high";


            sender.setParameters(params);
        });

        var offered = await receiver.peerConnection.createOffer();
        var offerDict = { sdp:offered.sdp, type:offered.type }
        console.log("[OFFER] : Offer created",offered);
        receiver.peerConnection.setLocalDescription(offered);
        console.log("[OFFER] : Offer sent");
        setDoc(offerDoc, offerDict);
    }
    catch (e) {
        console.error('[SERVER] Encountered error starting:', e);
    }
}

export function stopViewer() {
    try {
        console.log('[VIEWER] Stopping viewer connection');

        deleteDoc(offerDoc);
        deleteDoc(answerDoc);


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

        if (receiver.peerConnection) {
            receiver.peerConnection.close();
            receiver.peerConnection = null;
            receiver.peerConnection = null;
        }

        if (receiver.remoteStream) {
            receiver.remoteStream.getTracks().forEach(track => track.stop());
            receiver.remoteStream = null;
        }

        if (receiver.remoteView) {
            receiver.remoteView.srcObject = null;
        }

    } catch (e) {
        console.error('[VIEWER] Encountered error stopping', e);
    }
}


