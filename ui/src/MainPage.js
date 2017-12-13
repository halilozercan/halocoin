import React, { Component } from 'react';
import {MCardStats, MCardTable} from './components/card.js';
import $ from "jquery";
import Blockcount from './widgets/blockcount.js';
import {timestampToDatetime} from './tools.js';
import axios from 'axios';

class MainPage extends Component {

  constructor(props){
    super(props);
    this.state = {
      'default_wallet': null,
      'peers': {
        'columns': {},
        'rows': null
      },
      'txs': {
        'columns': {},
        'rows': null
      },
      'blocks': {
        'columns': {},
        'rows': null
      }
    }
    this.getDefaultWallet = this.getDefaultWallet.bind(this);
  }

  componentDidMount() {
    this.getDefaultWallet();
    this.initBlockchainStats();
  }

  getDefaultWallet() {
    $.get("/info_wallet", (data) => {
      if(data.hasOwnProperty('address')) {
        this.setState((state) => {
          state['default_wallet'] = data;
          return state;
        });
      }
      else {
        this.setState((state) => {
          state['default_wallet'] = null;
          return state;
        });
      }
    });
  }

  initBlockchainStats() {
    this.updateTxs();
    this.updatePeers();
    this.updateBlocks();
  }

  updateTxs() {
    axios.get("/txs").then((response) => {
      let data = response.data;
      const columns = {'from': 'Sender', 'to': 'Receiver', 'amount': 'Value'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 20) {
          let new_row = [];
          Object.keys(columns).map((col, j) => {
            new_row.push(row[col]);
          });
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['txs'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  updatePeers() {
    axios.get("/peers").then((response) => {
      let data = response.data;
      const columns = {'ip': 'IP Address', 'port': 'Port', 'rank': 'Rank', 'length': 'Blockcount'};
      const rows = [];
      data.map((row, i) => {
        if(row.rank < 30 && rows.length < 10) {
          let new_row = [];
          Object.keys(columns).map((col, j) => {
            new_row.push(row[col]);
          });
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['peers'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  updateBlocks() {
    axios.get("/block").then((response) => {
      let data = response.data.blocks;
      const columns = {'length': 'Height', 'time': 'Timestamp', 'txs_count': 'Transactions', 'miner': 'Mined by'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 10) {
          let new_row = [];
          new_row.push(row.length);
          new_row.push(timestampToDatetime(row.time));
          new_row.push(row.txs.length);
          new_row.push(row.miner);
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['blocks'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });

    this.blockcount.update();
  }

  render() {
    let txs = null;
    if(this.state.txs.rows !== null && this.state.txs.rows.length > 0) {
      txs = <div className="col-lg-6 col-md-12">
              <MCardTable color="green" title="Waiting Transactions" description="List of waiting transactions in the pool"
               columns={this.state.txs.columns} rows={this.state.txs.rows}/>
            </div>;
    }
    return (
      <div className="container-fluid">
        <div className="row">
          <Blockcount ref={(input)=>{this.blockcount = input;}}/>
        </div>
        <div className="row">
          {txs}
          <div className="col-lg-6 col-md-12">
            <MCardTable color="blue" title="Blocks" description="Most recent blocks"
             columns={this.state.blocks.columns} rows={this.state.blocks.rows}/>
          </div>
          <div className="col-lg-6 col-md-12">
            <MCardTable color="purple" title="Peers" description="List of top ranked peers in your network"
             columns={this.state.peers.columns} rows={this.state.peers.rows}/>
          </div>
        </div>
      </div>
    );
  }
}

export default MainPage;
