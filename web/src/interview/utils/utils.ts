export const string2tlv = (str: string, type: string) => {
  const typeBuffer = new Uint8Array(4);
  for (let i = 0; i < type.length; i += 1) {
    typeBuffer[i] = type.charCodeAt(i);
  }

  const valueBuffer = new TextEncoder().encode(str);
  const tlvBuffer = new Uint8Array(typeBuffer.length + 4 + valueBuffer.length);
  tlvBuffer.set(typeBuffer, 0);
  tlvBuffer[4] = (valueBuffer.length >> 24) & 0xff;
  tlvBuffer[5] = (valueBuffer.length >> 16) & 0xff;
  tlvBuffer[6] = (valueBuffer.length >> 8) & 0xff;
  tlvBuffer[7] = valueBuffer.length & 0xff;
  tlvBuffer.set(valueBuffer, 8);
  return tlvBuffer.buffer;
};

export const tlv2String = (tlvBuffer: ArrayBufferLike) => {
  const typeBuffer = new Uint8Array(tlvBuffer, 0, 4);
  const lengthBuffer = new Uint8Array(tlvBuffer, 4, 4);
  const valueBuffer = new Uint8Array(tlvBuffer, 8);

  let type = '';
  for (let i = 0; i < typeBuffer.length; i += 1) {
    type += String.fromCharCode(typeBuffer[i]);
  }

  const length =
    (lengthBuffer[0] << 24) | (lengthBuffer[1] << 16) | (lengthBuffer[2] << 8) | lengthBuffer[3];
  const value = new TextDecoder().decode(valueBuffer.subarray(0, length));
  return { type, value };
};

export const isMobile = () =>
  /Mobi|Android|iPhone|iPad|Windows Phone/i.test(window.navigator.userAgent) ||
  window.innerWidth < 767;
