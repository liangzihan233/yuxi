const logger = {
  debug: (...args: unknown[]) => {
    if ((window as any)._debug_mode) {
      console.log(...args);
    }
  },
};

export default logger;
