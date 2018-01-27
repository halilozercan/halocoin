import React, { Component } from 'react';
import axios from "axios";
import Paper from 'material-ui/Paper';
import Chip from 'material-ui/Chip';
import FontIcon from 'material-ui/FontIcon';
import Avatar from 'material-ui/Avatar';

const bottomBarStyle = {
  position: 'fixed', 
  backgroundColor: '#EEEEEE',
  left: 0, 
  bottom: 0,
  zIndex: 100,
  width: '100%',
  padding: 16
};

const styles = {
  chip: {
    margin: 4,
  },
  wrapper: {
    display: 'flex',
    flexWrap: 'wrap',
  },
};

class Blockcount extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'length': '-',
      'known_length': '-',
      'cpu_usage': 0
    }
  }

  componentWillMount() {
    this.update();
    this.props.socket.on('new_block', (socket) => {
      this.update();
    })
    this.props.socket.on('new_tx_in_pool', (socket) => {
      this.update();
    })
    this.props.socket.on('cpu_usage', (data) => {
      this.setState({
        cpu_usage: data['message']
      });
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

    axios.get("/mempool").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['tx_pool_size'] = data.length;
        return state;
      });
    });
  }

  render() {
    return (
      <Paper style={bottomBarStyle}  zDepth={5}>
        <div style={{"float":"left"}}>
          <Chip
            onClick={() => {this.props.notify("How many blocks are downloaded / How many exist.");}}
            style={styles.chip}
          >
            <Avatar icon={<FontIcon className="material-icons">view_headline</FontIcon>} />
            Blockcount: {this.state.length}/{this.state.known_length}
          </Chip>
        </div>
        <div style={{"float":"left"}}>
          <Chip
            style={styles.chip}
          >
            <Avatar icon={<FontIcon className="material-icons">compare_arrows</FontIcon>} />
            Cpu Usage: {this.state.cpu_usage}%
          </Chip>
        </div>
        <div style={{"float":"left"}}>
          <Chip
            onClick={() => {this.props.notify("Number of transactions that are waiting in the pool.")}}
            style={styles.chip}
          >
            <Avatar icon={<FontIcon className="material-icons">compare_arrows</FontIcon>} />
            Waiting Transactions: {this.state.tx_pool_size}
          </Chip>
        </div>
      </Paper>
    );
  }
}

export default Blockcount;