import React from "react";
import { AppBar, Toolbar, Typography } from "@mui/material";

const Header = () => {
  return (
    <AppBar position="static" style={{ marginBottom: "20px" }}>
      <Toolbar>
        <Typography variant="h5" component="div" style={{ flexGrow: 1, textAlign: "center" }}>
          AI Multi-Agent Scheduler Interface
        </Typography>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
