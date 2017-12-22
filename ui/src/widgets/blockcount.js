import React, { Component } from 'react';
import axios from "axios";
import Paper from 'material-ui/Paper';

const bottomBarStyle = {
  position: 'fixed', 
  left: 0, 
  bottom: 0,
  zIndex: 150,
  width: '100%',
  padding: 16
};

class Blockcount extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'length': '-',
      'known_length': '-'
    }
  }

  componentWillMount() {
    this.update();
    this.props.socket.on('new_block', (socket) => {
      this.update();
    })
  }

  update() {
    axios.get("/blockcount").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['length'] = data.length;
        if(data.known_length !== -1)
          state['known_length'] = data.known_length;
        else
          state['known_length'] = 'Unk';
        return state;
      });
    });
  }

  render() {
    return (
      <Paper style={bottomBarStyle}  zDepth={1}>
        Blockcount: {this.state.length}/{this.state.known_length}
      </Paper>
    );
  }
}

export default Blockcount;