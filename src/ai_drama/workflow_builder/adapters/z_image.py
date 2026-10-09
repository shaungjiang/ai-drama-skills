"""Z-Image Turbo adapter. Other/quantized variants require an evidenced imported graph."""
Z_IMAGE_TURBO = {"unet": "z_image_turbo_bf16.safetensors", "clip": "qwen_3_4b.safetensors", "vae": "ae.safetensors", "clip_type": "lumina2", "steps": 8, "cfg": 1.0, "sampler": "res_multistep", "scheduler": "simple", "shift": 3.0, "source": "https://docs.comfy.org/tutorials/image/z-image/z-image-turbo"}
