import React, { Component } from 'react';
import EngineStatus from './widgets/engine.js';

class Status extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row" style={{marginBottom:16}}>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <EngineStatus notify={this.props.notify} />
          </div>
        </div>
      </div>
    );
  }
}

export default Status;