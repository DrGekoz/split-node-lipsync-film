import sys, json, base64, io
from pathlib import Path
import torch
from PIL import Image
import numpy as np

MODEL = Path(__file__).resolve().parents[1] / 'models' / 'film_net_fp16.pt'
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
MODEL_OBJ = torch.jit.load(str(MODEL), map_location='cpu').eval().half().to(DEVICE)

def load(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    a = np.asarray(im, dtype=np.float32) / 255.0
    t = torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).half().to(DEVICE)
    return t, (w, h)

def main(req):
    a, size = load(req['frame1'])
    b, _ = load(req['frame2'])
    t = a.new_full((1, 1), float(req.get('time', 0.5)))
    with torch.inference_mode():
        out = MODEL_OBJ(a, b, t).clamp(0, 1)[0].float().permute(1, 2, 0).cpu().numpy()
    im = Image.fromarray((out * 255).astype(np.uint8), 'RGB')
    buf = io.BytesIO(); im.save(buf, format='PNG', compress_level=1)
    return {'ok': True, 'png_base64': base64.b64encode(buf.getvalue()).decode(), 'width': size[0], 'height': size[1], 'device': str(DEVICE)}

for line in sys.stdin:
    try:
        print(json.dumps(main(json.loads(line))), flush=True)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': repr(e)}), flush=True)
