import React, { Component } from 'react';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import Send from './widgets/send.js';
import Miner from './widgets/miner.js';
import Power from './widgets/power.js';
import Stake from './widgets/stake.js';
import JobListing from './widgets/job_listing.js';

class Mining extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row" style={{marginBottom:16}}>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Miner notify={this.props.notify} />
          </div>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Power socket={this.props.socket}/>
          </div>
        </div>
        <div className="row">
          <div className="col-lg-12 col-md-12 col-sm-12">
            <Stake wallet={this.props.default_wallet} notify={this.props.notify}/>
          </div>
        </div>
        <div className="row">
          <JobListing notify={this.props.notify}/>
        </div>
      </div>
    );
  }
}

export default Mining;