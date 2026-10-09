"""Qwen recipes: ordinary generation and reference editing remain distinct."""
QWEN_IMAGE = {"unet": "qwen_image_fp8_e4m3fn.safetensors", "clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "vae": "qwen_image_vae.safetensors", "clip_type": "qwen_image", "steps": 20, "cfg": 3.5, "sampler": "euler", "scheduler": "simple", "shift": 3.1, "source": "https://docs.comfy.org/tutorials/image/qwen/qwen-image"}
QWEN_EDIT = {**QWEN_IMAGE, "unet": "qwen_image_edit_fp8_e4m3fn.safetensors", "source": "https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit"}
