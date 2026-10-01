/* =========================================
   SmartStudy AI - 3D Background
========================================= */

document.addEventListener("DOMContentLoaded", () => {

    // Check Three.js
    if (typeof THREE === "undefined") {
        console.warn("Three.js not loaded.");
        return;
    }

    /* -----------------------------------------
       CANVAS
    ----------------------------------------- */

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
        60,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );

    camera.position.z = 8;


    const renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true
    });

    renderer.setPixelRatio(
        Math.min(window.devicePixelRatio, 2)
    );

    renderer.setSize(
        window.innerWidth,
        window.innerHeight
    );

    renderer.domElement.id = "three-background";

    renderer.domElement.style.position = "fixed";
    renderer.domElement.style.top = "0";
    renderer.domElement.style.left = "0";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.zIndex = "-1";
    renderer.domElement.style.pointerEvents = "none";

    document.body.prepend(renderer.domElement);


    /* -----------------------------------------
       PARTICLES
    ----------------------------------------- */

    const particleCount = 700;

    const positions = new Float32Array(
        particleCount * 3
    );

    for (let i = 0; i < particleCount; i++) {

        positions[i * 3] =
            (Math.random() - 0.5) * 25;

        positions[i * 3 + 1] =
            (Math.random() - 0.5) * 18;

        positions[i * 3 + 2] =
            (Math.random() - 0.5) * 15;
    }


    const particleGeometry =
        new THREE.BufferGeometry();

    particleGeometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            positions,
            3
        )
    );


    const particleMaterial =
        new THREE.PointsMaterial({

            color: 0x06b6d4,

            size: 0.035,

            transparent: true,

            opacity: 0.65
        });


    const particles =
        new THREE.Points(
            particleGeometry,
            particleMaterial
        );

    scene.add(particles);


    /* -----------------------------------------
       CENTRAL 3D NETWORK
    ----------------------------------------- */

    const geometry =
        new THREE.IcosahedronGeometry(
            2.8,
            2
        );

    const material =
        new THREE.MeshBasicMaterial({

            color: 0x2563eb,

            wireframe: true,

            transparent: true,

            opacity: 0.18
        });


    const network =
        new THREE.Mesh(
            geometry,
            material
        );

    network.position.set(
        2,
        0,
        -2
    );

    scene.add(network);


    /* -----------------------------------------
       SECOND GLOWING NETWORK
    ----------------------------------------- */

    const geometry2 =
        new THREE.IcosahedronGeometry(
            1.6,
            1
        );

    const material2 =
        new THREE.MeshBasicMaterial({

            color: 0x06b6d4,

            wireframe: true,

            transparent: true,

            opacity: 0.12
        });


    const network2 =
        new THREE.Mesh(
            geometry2,
            material2
        );

    network2.position.set(
        -3,
        1,
        -3
    );

    scene.add(network2);


    /* -----------------------------------------
       MOUSE MOVEMENT
    ----------------------------------------- */

    let mouseX = 0;
    let mouseY = 0;

    let targetX = 0;
    let targetY = 0;


    document.addEventListener(
        "mousemove",
        (event) => {

            mouseX =
                (event.clientX /
                    window.innerWidth) *
                2 - 1;

            mouseY =
                (event.clientY /
                    window.innerHeight) *
                2 - 1;

        }
    );


    /* -----------------------------------------
       ANIMATION
    ----------------------------------------- */

    const clock = new THREE.Clock();


    function animate() {

        requestAnimationFrame(animate);

        const time =
            clock.getElapsedTime();


        /* Particles */

        particles.rotation.y =
            time * 0.015;

        particles.rotation.x =
            time * 0.008;


        /* Main network */

        network.rotation.x =
            time * 0.08;

        network.rotation.y =
            time * 0.12;

        network.rotation.z =
            time * 0.04;


        /* Second network */

        network2.rotation.x =
            -time * 0.05;

        network2.rotation.y =
            time * 0.08;


        /* Mouse interaction */

        targetX = mouseX * 0.25;
        targetY = mouseY * 0.18;


        camera.position.x +=
            (targetX - camera.position.x) *
            0.02;

        camera.position.y +=
            (-targetY - camera.position.y) *
            0.02;


        camera.lookAt(
            scene.position
        );


        renderer.render(
            scene,
            camera
        );

    }


    animate();


    /* -----------------------------------------
       RESPONSIVE
    ----------------------------------------- */

    window.addEventListener(
        "resize",
        () => {

            camera.aspect =
                window.innerWidth /
                window.innerHeight;

            camera.updateProjectionMatrix();

            renderer.setSize(
                window.innerWidth,
                window.innerHeight
            );

        }
    );

});