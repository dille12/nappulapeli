# rl_agent.py
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

class LocalGoalAgent:
    """
    Small CNN that takes (H, W, 3) input:
      channel 0 = allied visibility (0..1)
      channel 1 = hostile visibility (0..1)
      channel 2 = position mask (1 at bot cell, else 0)
    Outputs a softmax over LOCAL_SIZE x LOCAL_SIZE possible local goal tiles.
    """

    def __init__(self,
                 map_h: int,
                 map_w: int,
                 local_size: int = 11,
                 conv_filters: int = 16,
                 latent_dim: int = 128,
                 dropout: float = 0.1,
                 build_model: bool = True):
        assert local_size % 2 == 1, "local_size must be odd (center tile exists)"
        self.map_h = map_h
        self.map_w = map_w
        self.local_size = local_size
        self.center = local_size // 2
        self.input_shape = (map_h, map_w, 4)
        self.conv_filters = conv_filters
        self.latent_dim = latent_dim
        self.dropout = dropout

        if build_model:
            self.model = self._build_model()
        else:
            self.model = None

    def _build_model(self):
        inputs = layers.Input(shape=self.input_shape, name="grid_input")  # (H, W, 3)

        # a few light conv blocks (keep it small)
        x = layers.Conv2D(self.conv_filters, 3, padding="same", activation="relu")(inputs)
        x = layers.Conv2D(self.conv_filters, 3, padding="same", activation="relu")(x)
        x = layers.MaxPool2D(2)(x)

        x = layers.Conv2D(self.conv_filters * 2, 3, padding="same", activation="relu")(x)
        x = layers.Conv2D(self.conv_filters * 2, 3, padding="same", activation="relu")(x)
        x = layers.MaxPool2D(2)(x)

        # preserve spatial information a bit further
        x = layers.Conv2D(self.conv_filters * 4, 3, padding="same", activation="relu")(x)
        x = layers.GlobalAveragePooling2D()(x)

        x = layers.Dense(self.latent_dim, activation="relu")(x)
        x = layers.Dropout(self.dropout)(x)

        # output logits for local_size ^ 2 cells
        out_dim = self.input_shape[0] * self.input_shape[1]
        logits = layers.Dense(out_dim, name="local_logits")(x)
        probs = layers.Softmax(name="local_prob")(logits)

        # Memory buffers
        self.memory = []  # list of (state, action, reward)

        model = models.Model(inputs=inputs, outputs=probs)
        model.compile(optimizer=tf.keras.optimizers.Adam(3e-4),
                      loss="categorical_crossentropy")  # training placeholder
        return model

    def predict_goal_tile(self, inputTensor: np.ndarray) -> np.ndarray:
        """
        Given an input tensor (H, W, C), returns a 2D probability map over all tiles (H, W).
        """
        # Add batch dimension
        input_batch = np.expand_dims(inputTensor, 0)  # shape: (1, H, W, C)

        # Forward pass
        logits = self.model(input_batch, training=False)[0]  # shape: (H*W,)

        # Reshape to 2D map
        H, W = self.input_shape[:2]
        probs2d = np.reshape(logits, (H, W))

        # Optional: normalize again in case of numerical issues
        probs2d = probs2d / np.sum(probs2d)

        return probs2d



    def predict_goal_tile_sample(self, allied_vis, hostile_vis, pos, temperature=1.0):
        """
        Sample from the model distribution (useful for exploration).
        """
        H, W = self.map_h, self.map_w
        pos_mask = np.zeros((H, W), dtype=np.float32)
        px, py = int(pos[0]), int(pos[1])
        if 0 <= px < W and 0 <= py < H:
            pos_mask[py, px] = 1.0
        inp = np.stack([allied_vis, hostile_vis, pos_mask], axis=-1)[None, ...]
        logits = self.model.predict(inp, verbose=0)[0]
        # temperature sampling
        logits = np.log(np.maximum(logits, 1e-9))
        logits = logits / max(1e-6, temperature)
        exp = np.exp(logits - np.max(logits))
        probs = exp / np.sum(exp)
        idx = np.random.choice(len(probs), p=probs)
        ly = idx // self.local_size
        lx = idx % self.local_size
        dx = lx - self.center
        dy = ly - self.center
        tx = int(np.clip(px + dx, 0, W - 1))
        ty = int(np.clip(py + dy, 0, H - 1))
        return (tx, ty), probs.reshape((self.local_size, self.local_size))

    def save(self, path: str):
        """Save model weights to path (HDF5 or tf format depending on tf version)."""
        if self.model is None:
            raise RuntimeError("Model not built")
        self.model.save(path)

    def load(self, path: str):
        self.model = tf.keras.models.load_model(path)

    @staticmethod
    def make_random_dummy_input(H, W):
        # helper to test prediction pipeline
        allied = np.zeros((H, W), dtype=np.float32)
        hostile = np.zeros((H, W), dtype=np.float32)
        px = W // 2
        py = H // 2
        allied[py, px] = 1.0
        return allied, hostile, (px, py)


if __name__ == "__main__":
    agent = LocalGoalAgent(80, 120)
    agent.model.summary()